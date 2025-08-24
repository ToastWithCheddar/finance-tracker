# Standard library imports
from typing import Dict, Any, List
from uuid import UUID
from collections import defaultdict

# Third-party imports
from sqlalchemy.orm import Session
from sqlalchemy import select

# Local imports
from ..models.plaid_recurring_transaction import PlaidRecurringTransaction
from ..models.account import Account
from ..schemas.plaid_recurring import (
    PlaidRecurringInsightsResponse, 
    PlaidRecurringTopSubscription,
    PlaidRecurringCostByAccount,
    PlaidRecurringTransactionResponse
)


class PlaidRecurringService:
    """Service for Plaid recurring transaction analytics and insights"""
    
    async def get_recurring_insights(self, db: Session, user_id: UUID) -> PlaidRecurringInsightsResponse:
        """
        Generate comprehensive insights from user's recurring transactions
        
        Args:
            db: Database session
            user_id: User ID to get insights for
            
        Returns:
            PlaidRecurringInsightsResponse with aggregated insights
        """
        # Get all recurring transactions for the user with account info
        query = (
            select(PlaidRecurringTransaction, Account.name.label('account_name'))
            .join(Account, PlaidRecurringTransaction.account_id == Account.id)
            .where(PlaidRecurringTransaction.user_id == user_id)
        )
        result = db.execute(query)
        transactions_with_accounts = result.all()
        
        # Initialize counters and aggregators
        total_subscriptions = len(transactions_with_accounts)
        total_monthly_cost_cents = 0
        active_subscriptions = 0
        muted_subscriptions = 0
        linked_subscriptions = 0
        
        frequency_breakdown = defaultdict(int)
        status_breakdown = defaultdict(int)
        cost_by_account_dict = defaultdict(lambda: {"account_name": "", "total_monthly_cents": 0, "subscription_count": 0})
        
        # Top subscriptions list (we'll sort by monthly cost)
        subscription_list = []
        
        # Process each transaction
        for row in transactions_with_accounts:
            transaction = row.PlaidRecurringTransaction
            account_name = row.account_name
            
            # Calculate monthly cost
            monthly_cost = transaction.monthly_estimated_amount_cents
            total_monthly_cost_cents += monthly_cost
            
            # Count by status
            if not transaction.is_muted:
                active_subscriptions += 1
            else:
                muted_subscriptions += 1
                
            if transaction.is_linked_to_rule:
                linked_subscriptions += 1
            
            # Frequency breakdown
            frequency_breakdown[transaction.plaid_frequency] += 1
            
            # Status breakdown
            status_breakdown[transaction.plaid_status] += 1
            
            # Cost by account
            account_key = str(transaction.account_id)
            cost_by_account_dict[account_key]["account_name"] = account_name
            cost_by_account_dict[account_key]["total_monthly_cents"] += monthly_cost
            cost_by_account_dict[account_key]["subscription_count"] += 1
            
            # Add to subscription list for top subscriptions
            subscription_list.append({
                "plaid_recurring_transaction_id": transaction.plaid_recurring_transaction_id,
                "description": transaction.description,
                "merchant_name": transaction.merchant_name,
                "monthly_estimated_amount_cents": monthly_cost,
                "frequency": transaction.plaid_frequency
            })
        
        # Sort subscriptions by monthly cost (highest first) and take top 10
        top_subscriptions_raw = sorted(
            subscription_list, 
            key=lambda x: x["monthly_estimated_amount_cents"], 
            reverse=True
        )[:10]
        
        # Convert to proper schema objects
        top_subscriptions = [
            PlaidRecurringTopSubscription(**sub) for sub in top_subscriptions_raw
        ]
        
        # Convert cost_by_account to the expected format
        cost_by_account = [
            PlaidRecurringCostByAccount(
                account_id=account_id,
                account_name=data["account_name"],
                total_monthly_cents=data["total_monthly_cents"],
                subscription_count=data["subscription_count"]
            )
            for account_id, data in cost_by_account_dict.items()
        ]
        
        return PlaidRecurringInsightsResponse(
            total_subscriptions=total_subscriptions,
            total_monthly_cost_cents=total_monthly_cost_cents,
            total_monthly_cost_dollars=total_monthly_cost_cents / 100.0,
            active_subscriptions=active_subscriptions,
            muted_subscriptions=muted_subscriptions,
            linked_subscriptions=linked_subscriptions,
            frequency_breakdown=dict(frequency_breakdown),
            status_breakdown=dict(status_breakdown),
            top_subscriptions=top_subscriptions,
            cost_by_account=cost_by_account
        )
    
    async def get_recurring_transactions(
        self, 
        db: Session, 
        user_id: UUID,
        status_filter: str = None,
        frequency_filter: str = None,
        is_muted: bool = None,
        is_linked: bool = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PlaidRecurringTransactionResponse]:
        """
        Get user's Plaid recurring transactions with optional filtering
        
        Args:
            db: Database session
            user_id: User ID to get transactions for
            status_filter: Filter by Plaid status (MATURE, EARLY_DETECTION, etc.)
            frequency_filter: Filter by frequency (WEEKLY, MONTHLY, etc.)
            is_muted: Filter by muted status
            is_linked: Filter by rule link status
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PlaidRecurringTransactionResponse objects
        """
        # Build query with filters
        query = (
            select(PlaidRecurringTransaction)
            .where(PlaidRecurringTransaction.user_id == user_id)
        )
        
        # Apply filters
        if status_filter:
            query = query.where(PlaidRecurringTransaction.plaid_status == status_filter)
        if frequency_filter:
            query = query.where(PlaidRecurringTransaction.plaid_frequency == frequency_filter)
        if is_muted is not None:
            query = query.where(PlaidRecurringTransaction.is_muted == is_muted)
        if is_linked is not None:
            query = query.where(PlaidRecurringTransaction.is_linked_to_rule == is_linked)
        
        # Apply pagination and ordering
        query = (
            query
            .order_by(PlaidRecurringTransaction.last_sync_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = db.execute(query)
        transactions = result.scalars().all()
        
        # Convert to response schema
        response_transactions = []
        for transaction in transactions:
            response_transactions.append(PlaidRecurringTransactionResponse(
                plaid_recurring_transaction_id=transaction.plaid_recurring_transaction_id,
                description=transaction.description,
                merchant_name=transaction.merchant_name,
                amount_cents=transaction.amount_cents,
                amount_dollars=transaction.amount_dollars,
                currency=transaction.currency,
                frequency=transaction.plaid_frequency,
                status=transaction.plaid_status,
                category=transaction.plaid_category,
                last_amount_cents=transaction.last_amount_cents,
                last_amount_dollars=transaction.last_amount_dollars,
                last_date=transaction.last_date.isoformat() if transaction.last_date else None,
                monthly_estimated_cents=transaction.monthly_estimated_amount_cents,
                monthly_estimated_dollars=transaction.monthly_estimated_amount_cents / 100.0,
                account_id=transaction.account_id,
                is_muted=transaction.is_muted,
                is_linked_to_rule=transaction.is_linked_to_rule,
                linked_rule_id=transaction.linked_rule_id,
                is_mature=transaction.is_mature,
                first_detected_at=transaction.first_detected_at,
                last_sync_at=transaction.last_sync_at,
                sync_count=transaction.sync_count
            ))
        
        return response_transactions