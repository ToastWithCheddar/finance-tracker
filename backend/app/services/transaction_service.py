# Standard library imports
import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

# Third-party imports
from fastapi import HTTPException, status
from sqlalchemy import or_, and_, func, extract, case, desc
from sqlalchemy.orm import Session, joinedload

# Local imports
from ..config import settings
from ..core.exceptions import (
    TransactionNotFoundError,
    AccountNotFoundError,
    ValidationError,
    BusinessLogicError,
    DataIntegrityError
)
from ..models.transaction import Transaction
from ..models.account import Account
from ..models.category import Category
from ..schemas.ml import MLCategorizationResponse
from ..schemas.transaction import (
    TransactionCreate, 
    TransactionUpdate, 
    TransactionFilter, 
    TransactionPagination, 
    TransactionResponse
)
from .ml_service import get_ml_client, MLServiceError
from .merchant_service import merchant_service

logger = logging.getLogger(__name__)

class TransactionService:
    @staticmethod
    async def create_transaction(db: Session, transaction: TransactionCreate, user_id: UUID) -> Transaction:
        # Enrich merchant if not provided but description exists
        if not transaction.merchant and transaction.description:
            try:
                merchant_result = merchant_service.recognize_merchant(transaction.description)
                if merchant_result.recognized_merchant and merchant_result.confidence_score >= 0.6:
                    transaction.merchant = merchant_result.recognized_merchant
                    logger.info(f"Auto-enriched merchant: '{transaction.description}' -> '{transaction.merchant}' (confidence: {merchant_result.confidence_score})")
            except Exception as e:
                logger.warning(f"Merchant enrichment failed: {str(e)}")
                # Continue without merchant enrichment
        
        # If category is not provided, try to predict it using ML service
        if not transaction.category_id and transaction.description:
            ml_client = get_ml_client()
            
            try:
                # Call the type-safe ML service
                ml_response = await ml_client.categorize_transaction(
                    description=transaction.description,
                    amount_cents=transaction.amount_cents,
                    merchant=getattr(transaction, 'merchant', None),
                    user_id=str(user_id)
                )
                
                if ml_response.success and ml_response.data:
                    categorization: MLCategorizationResponse = ml_response.data
                    
                    # Check confidence and decide
                    if categorization.confidence >= settings.ML_CONFIDENCE_THRESHOLD:
                        transaction.category_id = categorization.category_id
                        # Store ML metadata for potential feedback
                        transaction_metadata = {
                            "ml_predicted": True,
                            "ml_confidence": categorization.confidence,
                            "ml_reasoning": categorization.reasoning
                        }
                    else:
                        # Low confidence - for sync operations, continue without categorization
                        logger.info(f"ML prediction confidence too low ({categorization.confidence}) for automatic categorization")
                        logger.info("Transaction will be created without ML categorization")
                        # Continue without ML categorization
                else:
                    # ML service failed - log but don't fail transaction creation
                    error_msg = "Category prediction service unavailable"
                    if ml_response.error:
                        error_msg = ml_response.error.message
                    
                    logger.warning(f"ML categorization failed: {error_msg}")
                    logger.info("Transaction will be created without ML categorization")
                    # Continue without ML categorization
                    
            except HTTPException as e:
                # For automatic transaction sync, don't fail if ML service is unavailable
                # Only re-raise if this is an interactive user operation (not a sync)
                logger.warning(f"ML categorization failed during transaction creation: {str(e)}")
                logger.info("Transaction will be created without ML categorization")
                # Continue without ML categorization
            except Exception as e:
                # Catch-all for other errors - also don't fail for sync operations
                logger.warning(f"Unexpected error during ML categorization: {str(e)}")
                logger.info("Transaction will be created without ML categorization")
                # Continue without ML categorization

        # Get transaction data for database - exclude 'amount' field as Transaction model uses 'amount_cents'
        transaction_data = transaction.model_dump(exclude={'amount', 'transaction_type'})
        
        db_transaction = Transaction(
            user_id=user_id,
            **transaction_data
        )
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction
    
    @staticmethod
    async def submit_ml_feedback(
        db: Session, 
        transaction_id: UUID, 
        correct_category_id: UUID, 
        user_id: UUID
    ) -> bool:
        """
        Submit feedback to ML service when user corrects a category
        """
        # Get the transaction
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            return False
            
        ml_client = get_ml_client()
        
        try:
            # Extract ML metadata if available
            metadata = transaction.metadata_json or {}
            predicted_category_id = transaction.ml_suggested_category_id
            confidence = transaction.confidence_score
            
            # Submit feedback
            feedback_response = await ml_client.submit_feedback(
                transaction_id=transaction_id,
                description=transaction.description,
                amount_cents=transaction.amount_cents,
                correct_category_id=correct_category_id,
                user_id=str(user_id),
                merchant=transaction.merchant,
                predicted_category_id=predicted_category_id,
                confidence=confidence
            )
            
            if feedback_response.success:
                # Update transaction metadata to record feedback submission
                metadata["ml_feedback_submitted"] = True
                metadata["ml_feedback_timestamp"] = datetime.utcnow().isoformat()
                transaction.metadata_json = metadata
                db.commit()
                return True
            else:
                logger.error(f"Failed to submit ML feedback: {feedback_response.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting ML feedback: {str(e)}")
            return False

    @staticmethod
    def get_transaction(db: Session, transaction_id: UUID, user_id: UUID) -> Transaction:
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            raise TransactionNotFoundError(str(transaction_id))
        
        return transaction

    @staticmethod
    def update_transaction(
        db: Session,
        transaction: Transaction,
        transaction_update: TransactionUpdate
    ) -> Transaction:
        update_data = transaction_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(transaction, field, value)
        
        transaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def delete_transaction(db: Session, transaction: Transaction) -> bool:
        db.delete(transaction)
        db.commit()
        return True

    @staticmethod
    def bulk_delete_transactions(db: Session, user_id: UUID, transaction_ids: List[UUID]) -> List[UUID]:
        """
        Efficiently delete multiple transactions in a single database operation.
        Returns list of successfully deleted transaction IDs.
        """
        try:
            # First verify ownership and get existing transactions in one query
            existing_transactions = db.query(Transaction.id).filter(
                Transaction.user_id == user_id,
                Transaction.id.in_(transaction_ids)
            ).all()
            
            existing_ids = [str(tx.id) for tx in existing_transactions]
            
            if not existing_ids:
                return []
            
            # Perform bulk delete in single query
            num_deleted = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.id.in_(existing_ids)
            ).delete(synchronize_session=False)
            
            db.commit()
            
            # Return the IDs that were actually deleted
            return [UUID(tx_id) for tx_id in existing_ids[:num_deleted]]
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error during bulk delete: {str(e)}", exc_info=True)
            raise DataIntegrityError("Failed to delete transactions due to database constraints")

    @staticmethod
    def get_transactions_with_filters(
        db: Session,
        user_id: UUID,
        filters: TransactionFilter,
        pagination: TransactionPagination
    ) -> Tuple[List[Transaction], int]:
        # Use eager loading to prevent N+1 queries
        query = db.query(Transaction).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        ).join(Transaction.account).filter(Transaction.user_id == user_id)

        # Apply filters
        if filters.start_date:
            query = query.filter(Transaction.transaction_date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Transaction.transaction_date <= filters.end_date)
        if filters.category_id:
            if filters.category_id == '__uncategorized__':
                query = query.filter(Transaction.category_id.is_(None))
            else:
                query = query.filter(Transaction.category_id == filters.category_id)
        if filters.status:
            query = query.filter(Transaction.status == filters.status)
        if filters.min_amount_cents is not None:
            query = query.filter(Transaction.amount_cents >= filters.min_amount_cents)
        if filters.max_amount_cents is not None:
            query = query.filter(Transaction.amount_cents <= filters.max_amount_cents)
        if filters.account_id:
            query = query.filter(Transaction.account_id == filters.account_id)
        if filters.is_recurring is not None:
            query = query.filter(Transaction.is_recurring == filters.is_recurring)
        if filters.is_transfer is not None:
            query = query.filter(Transaction.is_transfer == filters.is_transfer)
        if filters.search_query:
            search = f"%{filters.search_query}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search),
                    Transaction.merchant.ilike(search),
                    Transaction.notes.ilike(search),
                    Category.name.ilike(search)
                )
            )
        if filters.tags:
            # Assuming tags is stored as JSON array - adjust based on actual implementation
            for tag in filters.tags:
                query = query.filter(Transaction.tags.contains([tag]))

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset((pagination.page - 1) * pagination.per_page)
        query = query.limit(pagination.per_page)

        return query.all(), total_count

    @staticmethod
    def get_transactions_with_grouping(
        db: Session,
        user_id: UUID,
        filters: TransactionFilter,
        pagination: TransactionPagination
    ) -> Dict[str, Any]:
        """Get transactions with server-side grouping"""
        from ..schemas.transaction import TransactionGroupBy
        
        # Use eager loading to prevent N+1 queries for grouping
        query = db.query(Transaction).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        ).join(Transaction.account).filter(Transaction.user_id == user_id)

        # Apply all the same filters as the regular method
        if filters.start_date:
            query = query.filter(Transaction.transaction_date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Transaction.transaction_date <= filters.end_date)
        if filters.category_id:
            if filters.category_id == '__uncategorized__':
                query = query.filter(Transaction.category_id.is_(None))
            else:
                query = query.filter(Transaction.category_id == filters.category_id)
        if filters.status:
            query = query.filter(Transaction.status == filters.status)
        if filters.min_amount_cents is not None:
            query = query.filter(Transaction.amount_cents >= filters.min_amount_cents)
        if filters.max_amount_cents is not None:
            query = query.filter(Transaction.amount_cents <= filters.max_amount_cents)
        if filters.account_id:
            query = query.filter(Transaction.account_id == filters.account_id)
        if filters.is_recurring is not None:
            query = query.filter(Transaction.is_recurring == filters.is_recurring)
        if filters.is_transfer is not None:
            query = query.filter(Transaction.is_transfer == filters.is_transfer)
        if filters.search_query:
            search = f"%{filters.search_query}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search),
                    Transaction.merchant.ilike(search),
                    Transaction.notes.ilike(search),
                    Category.name.ilike(search)
                )
            )
        if filters.tags:
            for tag in filters.tags:
                query = query.filter(Transaction.tags.contains([tag]))

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination to the query
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset((pagination.page - 1) * pagination.per_page)
        query = query.limit(pagination.per_page)
        
        # Get the transactions
        transactions = query.all()
        
        # Group the transactions based on group_by parameter
        groups = {}
        group_by = filters.group_by
        
        for transaction in transactions:
            # Determine the group key based on grouping type
            if group_by == TransactionGroupBy.DATE:
                group_key = transaction.transaction_date.strftime('%Y-%m-%d')
            elif group_by == TransactionGroupBy.CATEGORY:
                group_key = transaction.category.name if transaction.category else "Uncategorized"
            elif group_by == TransactionGroupBy.MERCHANT:
                group_key = transaction.merchant if transaction.merchant else "Unknown Merchant"
            else:
                # Default to date grouping
                group_key = transaction.transaction_date.strftime('%Y-%m-%d')
            
            if group_key not in groups:
                groups[group_key] = {
                    "key": group_key,
                    "total_amount_cents": 0,
                    "count": 0,
                    "transactions": []
                }
            
            groups[group_key]["total_amount_cents"] += transaction.amount_cents
            groups[group_key]["count"] += 1
            groups[group_key]["transactions"].append(transaction)
        
        # Sort groups appropriately
        if group_by == TransactionGroupBy.DATE:
            sorted_groups = sorted(groups.values(), key=lambda x: x["key"], reverse=True)
        else:
            # For category and merchant, sort alphabetically
            sorted_groups = sorted(groups.values(), key=lambda x: x["key"])
        
        return {
            "groups": sorted_groups,
            "total": total_count,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": (total_count + pagination.per_page - 1) // pagination.per_page,
            "grouped": True
        }

    @staticmethod
    def import_transactions_from_csv(
        db: Session,
        user_id: UUID,
        transactions: List[TransactionCreate]
    ) -> List[Transaction]:
        db_transactions = []
        for transaction in transactions:
            # Exclude 'amount' field as Transaction model uses 'amount_cents'
            transaction_data = transaction.model_dump(exclude={'amount', 'transaction_type'})
            db_transaction = Transaction(
                user_id=user_id,
                **transaction_data
            )
            db_transactions.append(db_transaction)

        db.add_all(db_transactions)
        db.commit()
        
        for transaction in db_transactions:
            db.refresh(transaction)
        
        return db_transactions

    @staticmethod
    def stream_transactions_for_export(
        db: Session, 
        user_id: UUID, 
        filters: TransactionFilter, 
        chunk_size: int = 1000
    ):
        """
        Stream transactions in chunks for efficient export processing.
        Yields batches of transactions to avoid loading all data into memory.
        """
        from sqlalchemy.orm import joinedload
        
        # Build base query with filters
        query = db.query(Transaction).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        ).join(Transaction.account).filter(Transaction.user_id == user_id)
        
        # Apply filters (same logic as get_transactions_with_filters)
        if filters.start_date:
            query = query.filter(Transaction.transaction_date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Transaction.transaction_date <= filters.end_date)
        if filters.category:
            query = query.join(Transaction.category).filter(Category.name.ilike(f"%{filters.category}%"))
        if filters.search_query:
            search_term = f"%{filters.search_query}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search_term),
                    Transaction.merchant_name.ilike(search_term)
                )
            )
        
        # Order by transaction_date for consistent export ordering
        query = query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at))
        
        # Stream in chunks
        offset = 0
        while True:
            chunk = query.offset(offset).limit(chunk_size).all()
            if not chunk:
                break
            yield chunk
            offset += chunk_size

    @staticmethod
    def get_dashboard_analytics(db: Session, user_id: UUID, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive dashboard analytics for a user - delegated to analytics service"""
        from .transaction_analytics_service import transaction_analytics_service
        return transaction_analytics_service.get_dashboard_analytics(db, user_id, start_date, end_date)

    @staticmethod
    def get_transaction_summary(db: Session, user_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None, category_id: Optional[UUID] = None, search_query: Optional[str] = None) -> Dict[str, Any]:
        """Get transaction summary statistics - delegated to analytics service"""
        from .transaction_analytics_service import transaction_analytics_service
        return transaction_analytics_service.get_transaction_summary(db, user_id, start_date, end_date, category_id, search_query)

    @staticmethod
    def get_spending_trends(db: Session, user_id: UUID, period: str = "monthly") -> List[Dict[str, Any]]:
        """Get spending trends over time - delegated to analytics service"""
        from .transaction_analytics_service import transaction_analytics_service
        return transaction_analytics_service.get_spending_trends(db, user_id, period) 