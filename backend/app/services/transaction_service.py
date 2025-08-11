# Standard library imports
import json
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

# Third-party imports
from fastapi import HTTPException, status
from sqlalchemy import or_, and_, func, extract, case
from sqlalchemy.orm import Session, joinedload

# Local imports
from ..config import settings
from ..core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
    BusinessLogicException,
    ExternalServiceException,
    ErrorCode,
    ErrorDetail,
    create_validation_error
)
from ..models.transaction import Transaction
from ..models.account import Account
from ..schemas.ml import MLCategorizationResponse
from ..schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilter, TransactionPagination
from .ml_client import get_ml_client, MLServiceError

logger = logging.getLogger(__name__)

class TransactionService:
    @staticmethod
    async def create_transaction(db: Session, transaction: TransactionCreate, user_id: UUID) -> Transaction:
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
                    
            except (BusinessLogicException, ExternalServiceException) as e:
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

        # Get transaction data for database
        transaction_data = transaction.model_dump()
        
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
            raise ResourceNotFoundException("Transaction", str(transaction_id))
        
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
                    Transaction.merchant.ilike(search)
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
    def import_transactions_from_csv(
        db: Session,
        user_id: UUID,
        transactions: List[TransactionCreate]
    ) -> List[Transaction]:
        db_transactions = []
        for transaction in transactions:
            db_transaction = Transaction(
                user_id=user_id,
                **transaction.model_dump()
            )
            db_transactions.append(db_transaction)

        db.add_all(db_transactions)
        db.commit()
        
        for transaction in db_transactions:
            db.refresh(transaction)
        
        return db_transactions

    @staticmethod
    def get_dashboard_analytics(db: Session, user_id: UUID, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive dashboard analytics for a user"""
        
        # If no date range provided, use current month
        if not start_date:
            now = datetime.now()
            start_date = datetime(now.year, now.month, 1)
        if not end_date:
            end_date = datetime.now()

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )

        # Get all transactions in the period
        transactions = query.all()

        # Calculate totals (convert from cents to dollars)
        total_income = sum(t.amount_cents for t in transactions if t.amount_cents > 0) / 100.0
        total_expenses = sum(abs(t.amount_cents) for t in transactions if t.amount_cents < 0) / 100.0
        net_amount = total_income - total_expenses

        # Get category breakdown
        category_stats = {}
        for transaction in transactions:
            category_name = "Food & Dining"  # TODO: Get actual category name from relationship
            if category_name not in category_stats:
                category_stats[category_name] = {
                    "total_amount": 0,
                    "transaction_count": 0,
                    "category_name": category_name
                }
            category_stats[category_name]["total_amount"] += abs(transaction.amount_cents / 100.0)
            category_stats[category_name]["transaction_count"] += 1

        # Convert to list and calculate percentages
        category_breakdown = []
        total_for_percentage = total_expenses if total_expenses > 0 else 1  # Avoid division by zero
        
        for category, stats in category_stats.items():
            percentage = (stats["total_amount"] / total_for_percentage) * 100 if stats["total_amount"] < 0 else 0
            category_breakdown.append({
                "category_name": category,
                "total_amount": stats["total_amount"],
                "transaction_count": stats["transaction_count"],
                "percentage": round(percentage, 2)
            })

        # Sort by total amount descending
        category_breakdown.sort(key=lambda x: x["total_amount"], reverse=True)

        # Get recent transactions (last 10)
        recent_transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.transaction_date.desc()).limit(10).all()

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_amount": net_amount,
                "transaction_count": len(transactions)
            },
            "category_breakdown": category_breakdown,
            "recent_transactions": [
                {
                    "id": t.id,
                    "amount": t.amount_cents / 100.0,
                    "category": "Food & Dining",  # TODO: Get actual category name
                    "description": t.description,
                    "transaction_date": t.transaction_date.isoformat(),
                    "transaction_type": "income" if t.amount_cents > 0 else "expense"
                } for t in recent_transactions
            ]
        }

    @staticmethod
    def get_transaction_summary(db: Session, user_id: UUID, start_date: Optional[date] = None, end_date: Optional[date] = None, category_id: Optional[UUID] = None, search_query: Optional[str] = None) -> Dict[str, Any]:
        """Get transaction summary statistics matching the frontend TransactionSummary interface"""
        from sqlalchemy import or_
        
        # Build base query
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        
        # Apply filters
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if search_query:
            search = f"%{search_query}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search),
                    Transaction.merchant.ilike(search)
                )
            )
        
        # Get all matching transactions
        transactions = query.all()
        
        # Calculate summary statistics
        total_income = sum(t.amount_cents for t in transactions if t.amount_cents > 0) / 100.0
        total_expenses = sum(abs(t.amount_cents) for t in transactions if t.amount_cents < 0) / 100.0
        net_amount = total_income - total_expenses
        transaction_count = len(transactions)
        
        # Calculate category breakdown
        category_stats = {}
        total_for_percentage = total_expenses if total_expenses > 0 else 1
        
        for transaction in transactions:
            # Get category info (assuming there's a relationship)
            category_id_str = str(transaction.category_id) if transaction.category_id else "uncategorized"
            category_name = "Uncategorized"  # Default name
            
            # Try to get category name if there's a relationship
            if hasattr(transaction, 'category') and transaction.category:
                category_name = transaction.category.name
            
            if category_id_str not in category_stats:
                category_stats[category_id_str] = {
                    "categoryId": category_id_str,
                    "categoryName": category_name,
                    "totalAmount": 0.0,
                    "transactionCount": 0
                }
            
            category_stats[category_id_str]["totalAmount"] += abs(transaction.amount_cents) / 100.0
            category_stats[category_id_str]["transactionCount"] += 1
        
        # Convert to list and add percentages
        category_breakdown = []
        for category_id_str, stats in category_stats.items():
            percentage = (stats["totalAmount"] / total_for_percentage) * 100 if total_for_percentage > 0 else 0
            category_breakdown.append({
                "categoryId": stats["categoryId"],
                "categoryName": stats["categoryName"], 
                "totalAmount": stats["totalAmount"],
                "transactionCount": stats["transactionCount"],
                "percentage": round(percentage, 2)
            })
        
        # Sort by total amount descending
        category_breakdown.sort(key=lambda x: x["totalAmount"], reverse=True)
        
        return {
            "totalIncome": total_income,
            "totalExpenses": total_expenses, 
            "netAmount": net_amount,
            "transactionCount": transaction_count,
            "categoryBreakdown": category_breakdown
        }

    @staticmethod
    def get_spending_trends(db: Session, user_id: UUID, period: str = "monthly") -> List[Dict[str, Any]]:
        """Get spending trends over time"""
        
        # Calculate date range based on period
        now = datetime.now()
        if period == "weekly":
            start_date = now - timedelta(weeks=12)  # Last 12 weeks
            date_format = "week"
        else:  # monthly
            start_date = now - timedelta(days=365)  # Last 12 months
            date_format = "month"

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date
        )

        transactions = query.all()

        # Group by time period
        trends = {}
        for transaction in transactions:
            if period == "weekly":
                # Get week number and year
                year = transaction.transaction_date.year
                week = transaction.transaction_date.isocalendar()[1]
                key = f"{year}-W{week:02d}"
                display_date = transaction.transaction_date.strftime("%Y-W%U")
            else:  # monthly
                key = transaction.transaction_date.strftime("%Y-%m")
                display_date = transaction.transaction_date.strftime("%Y-%m")

            if key not in trends:
                trends[key] = {
                    "period": display_date,
                    "income": 0,
                    "expenses": 0,
                    "net": 0
                }

            if transaction.amount_cents > 0:
                trends[key]["income"] += transaction.amount_cents / 100.0
            else:
                trends[key]["expenses"] += abs(transaction.amount_cents / 100.0)
            trends[key]["net"] = trends[key]["income"] - trends[key]["expenses"]

        # Convert to sorted list
        trend_list = list(trends.values())
        trend_list.sort(key=lambda x: x["period"])

        return trend_list 