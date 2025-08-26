# Standard library imports
import json
import logging
from datetime import datetime, timedelta, date, timezone
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
from ..models.user import User
from ..schemas.ml import MLCategorizationResponse
from ..schemas.transaction import (
    TransactionCreate,
    TransactionUpdate, 
    TransactionFilter, 
    TransactionPagination, 
    TransactionResponse
)
from .ml_service import get_ml_client, MLServiceError
from .merchant_service import get_merchant_service

logger = logging.getLogger(__name__)

class TransactionService:
    @staticmethod
    async def create_transaction(db: Session, transaction: TransactionCreate, user_id: UUID, user: Optional[User] = None) -> Transaction:
        # Enrich merchant if not provided but description exists
        if not transaction.merchant and transaction.description:
            try:
                merchant_result = get_merchant_service().recognize_merchant(transaction.description)
                if merchant_result.recognized_merchant and merchant_result.confidence_score >= 0.6:
                    transaction.merchant = merchant_result.recognized_merchant
                    logger.info(f"Auto-enriched merchant: '{transaction.description}' -> '{transaction.merchant}' (confidence: {merchant_result.confidence_score})")
            except Exception as e:
                logger.warning(f"Merchant enrichment failed: {str(e)}")
                # Continue without merchant enrichment
        
        # If category is not provided, try to predict it using ML service (if user enabled)
        if not transaction.category_id and transaction.description:
            # Get user object if not provided
            if user is None:
                user = db.query(User).filter(User.id == user_id).first()
            
            # Check if user has ML auto-categorization enabled
            if user and user.auto_categorization_enabled:
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
                            # Validate that the suggested category belongs to the user
                            from ..models.category import Category
                            suggested_category = db.query(Category).filter(
                                Category.id == categorization.category_id,
                                Category.user_id == user_id
                            ).first()
                            
                            if suggested_category:
                                transaction.category_id = categorization.category_id
                                # Store ML metadata for potential feedback
                                transaction_metadata = {
                                    "ml_predicted": True,
                                    "ml_confidence": categorization.confidence,
                                    "ml_reasoning": categorization.reasoning
                                }
                                logger.info(f"Applied ML categorization: '{categorization.category_name}' (confidence: {categorization.confidence})")
                            else:
                                logger.warning(f"ML suggested invalid category (ID: {categorization.category_id}) - category not found or not owned by user")
                                # Try to find a similar category by name
                                if categorization.category_name:
                                    similar_category = db.query(Category).filter(
                                        Category.user_id == user_id,
                                        Category.name.ilike(f"%{categorization.category_name}%")
                                    ).first()
                                    
                                    if similar_category:
                                        transaction.category_id = similar_category.id
                                        logger.info(f"Found similar user category: '{similar_category.name}' for ML suggestion '{categorization.category_name}'")
                                    else:
                                        logger.info("No similar user category found - transaction will remain uncategorized")
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
            else:
                logger.debug("ML auto-categorization disabled for user or user not found")

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
    def get_transaction(db: Session, transaction_id: UUID, user_id: UUID) -> Transaction:
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            raise TransactionNotFoundError(str(transaction_id))
        
        return transaction

    @staticmethod
    async def update_transaction(
        db: Session,
        transaction: Transaction,
        transaction_update: TransactionUpdate
    ) -> Transaction:
        update_data = transaction_update.model_dump(exclude_unset=True)
        
        # Check if category is being updated (for ML learning)
        category_changed = 'category_id' in update_data and update_data['category_id'] != transaction.category_id
        new_category_id = update_data.get('category_id') if category_changed else None
        
        for field, value in update_data.items():
            setattr(transaction, field, value)
        
        transaction.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(transaction)
        
        # If category was manually updated, add this as a training example for ML
        if category_changed and new_category_id and transaction.description:
            try:
                # Get the category name for ML training
                from ..models.category import Category
                category = db.query(Category).filter(Category.id == new_category_id).first()
                
                if category:
                    # Prepare training example
                    training_text = transaction.description
                    if transaction.merchant:
                        training_text = f"{transaction.merchant} {transaction.description}"
                    
                    # Add training example to ML service asynchronously
                    ml_client = get_ml_client()
                    ml_response = await ml_client.add_training_example(
                        category=category.name,
                        example=training_text,
                        user_id=str(transaction.user_id)
                    )
                    
                    if ml_response.success:
                        logger.info(f"Added ML training example: '{training_text}' -> '{category.name}'")
                    else:
                        logger.warning(f"Failed to add ML training example: {ml_response.error.message if ml_response.error else 'Unknown error'}")
                        
            except Exception as e:
                # Don't fail the transaction update if ML training fails
                logger.warning(f"ML training example failed: {str(e)}")
        
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
        logger.info(f"🔍 [TransactionService] Getting transactions for user {user_id} with filters: {filters.model_dump()}")
        
        # Use eager loading to prevent N+1 queries
        query = db.query(Transaction).options(
            joinedload(Transaction.account),
            joinedload(Transaction.category)
        ).join(Transaction.account).filter(Transaction.user_id == user_id)

        applied_filters = []

        # Apply filters with logging
        if filters.start_date:
            query = query.filter(Transaction.transaction_date >= filters.start_date)
            applied_filters.append(f"start_date >= {filters.start_date}")
            
        if filters.end_date:
            query = query.filter(Transaction.transaction_date <= filters.end_date)
            applied_filters.append(f"end_date <= {filters.end_date}")
            
        if filters.category_id:
            if str(filters.category_id) == '__uncategorized__':
                query = query.filter(Transaction.category_id.is_(None))
                applied_filters.append("category_id IS NULL (uncategorized)")
            else:
                query = query.filter(Transaction.category_id == filters.category_id)
                applied_filters.append(f"category_id = {filters.category_id}")
                
        if filters.status:
            query = query.filter(Transaction.status == filters.status)
            applied_filters.append(f"status = {filters.status}")
            
        if filters.min_amount_cents is not None:
            query = query.filter(Transaction.amount_cents >= filters.min_amount_cents)
            applied_filters.append(f"amount_cents >= {filters.min_amount_cents}")
            
        if filters.max_amount_cents is not None:
            query = query.filter(Transaction.amount_cents <= filters.max_amount_cents)
            applied_filters.append(f"amount_cents <= {filters.max_amount_cents}")
            
        if filters.account_id:
            query = query.filter(Transaction.account_id == filters.account_id)
            applied_filters.append(f"account_id = {filters.account_id}")
            
        
        if filters.is_transfer is not None:
            query = query.filter(Transaction.is_transfer == filters.is_transfer)
            applied_filters.append(f"is_transfer = {filters.is_transfer}")
            
        if filters.search_query:
            search = f"%{filters.search_query}%"
            search_filter = or_(
                Transaction.description.ilike(search),
                Transaction.merchant.ilike(search),
                Transaction.notes.ilike(search),
                Category.name.ilike(search)
            )
            query = query.filter(search_filter)
            applied_filters.append(f"search_query ILIKE '%{filters.search_query}%' (description, merchant, notes, category)")
            
        if filters.tags:
            # Assuming tags is stored as JSON array - adjust based on actual implementation
            for tag in filters.tags:
                query = query.filter(Transaction.tags.contains([tag]))
                applied_filters.append(f"tags contains '{tag}'")

        logger.info(f"🔍 [TransactionService] Applied filters: {applied_filters}")

        # Get total count for pagination
        total_count = query.count()
        logger.info(f"🔍 [TransactionService] Total count before pagination: {total_count}")

        # Apply pagination
        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset(pagination.offset)
        query = query.limit(pagination.limit)

        results = query.all()
        logger.info(f"🔍 [TransactionService] Returned {len(results)} transactions after pagination (offset: {pagination.offset}, limit: {pagination.limit})")

        return results, total_count

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
        query = query.offset(pagination.offset)
        query = query.limit(pagination.limit)
        
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
            "limit": pagination.limit,
            "offset": pagination.offset,
            "has_more": total_count > pagination.offset + len(sorted_groups),
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
    def get_transaction_histogram(
        db: Session,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[str] = None,
        account_id: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        bins: int = 10
    ) -> dict:
        """Get histogram data for transaction amounts"""
        import numpy as np
        import statistics
        
        # Build base query
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Apply filters
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if category_id:
            try:
                category_uuid = UUID(category_id)
                query = query.filter(Transaction.category_id == category_uuid)
            except ValueError:
                pass  # Skip invalid UUID
        if account_id:
            try:
                account_uuid = UUID(account_id)
                query = query.filter(Transaction.account_id == account_uuid)
            except ValueError:
                pass  # Skip invalid UUID
        if amount_min is not None:
            amount_min_cents = int(amount_min * 100)
            query = query.filter(func.abs(Transaction.amount_cents) >= amount_min_cents)
        if amount_max is not None:
            amount_max_cents = int(amount_max * 100)
            query = query.filter(func.abs(Transaction.amount_cents) <= amount_max_cents)
        
        # Get all transaction amounts (absolute values for histogram)
        transactions = query.all()
        
        if not transactions:
            return {
                "bins": [],
                "statistics": {
                    "total_transactions": 0,
                    "total_amount": 0,
                    "mean_amount": 0,
                    "median_amount": 0,
                    "min_amount": 0,
                    "max_amount": 0
                },
                "filters_applied": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "category_id": category_id,
                    "account_id": account_id,
                    "amount_min": amount_min,
                    "amount_max": amount_max
                }
            }
        
        # Convert to dollar amounts (absolute values)
        amounts = [abs(t.amount_cents) / 100.0 for t in transactions]
        total_amount_cents = sum(t.amount_cents for t in transactions)
        
        # Calculate statistics
        mean_amount = statistics.mean(amounts)
        median_amount = statistics.median(amounts)
        min_amount = min(amounts)
        max_amount = max(amounts)
        
        # Create histogram bins
        if max_amount == min_amount:
            # All amounts are the same, create a single bin
            bin_edges = [min_amount - 0.01, max_amount + 0.01]
        else:
            bin_edges = np.linspace(min_amount, max_amount, bins + 1)
        
        # Calculate histogram
        hist_counts, _ = np.histogram(amounts, bins=bin_edges)
        
        # Build response bins
        response_bins = []
        for i in range(len(hist_counts)):
            range_min = bin_edges[i]
            range_max = bin_edges[i + 1]
            count = int(hist_counts[i])
            
            # Calculate total amount in this bin
            bin_transactions = [t for t in transactions 
                             if range_min <= abs(t.amount_cents) / 100.0 <= range_max]
            bin_total_amount = sum(abs(t.amount_cents) for t in bin_transactions) / 100.0
            
            # Format range label
            if range_min < 1:
                range_label = f"${range_min:.2f} - ${range_max:.2f}"
            elif range_max < 1000:
                range_label = f"${range_min:.0f} - ${range_max:.0f}"
            else:
                range_label = f"${range_min:.0f} - ${range_max:.0f}"
            
            response_bins.append({
                "range_min": range_min,
                "range_max": range_max,
                "count": count,
                "amount_total": bin_total_amount,
                "range_label": range_label
            })
        
        return {
            "bins": response_bins,
            "statistics": {
                "total_transactions": len(transactions),
                "total_amount": total_amount_cents / 100.0,
                "mean_amount": mean_amount,
                "median_amount": median_amount,
                "min_amount": min_amount,
                "max_amount": max_amount
            },
            "filters_applied": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "category_id": category_id,
                "account_id": account_id,
                "amount_min": amount_min,
                "amount_max": amount_max
            }
        }


# Provider function with lazy caching
_transaction_service_instance = None

def get_transaction_service() -> TransactionService:
    """Get the global TransactionService instance with lazy initialization"""
    global _transaction_service_instance
    if _transaction_service_instance is None:
        _transaction_service_instance = TransactionService()
    return _transaction_service_instance 