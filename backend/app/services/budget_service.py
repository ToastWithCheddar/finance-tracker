from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from decimal import Decimal
import uuid

from ..models.budget import Budget
from ..models.transaction import Transaction
from ..models.category import Category
from ..models.insight import Insight
from ..schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetUsage, 
    BudgetAlert, BudgetSummary, BudgetProgress, BudgetFilter,
    BudgetPeriod
)


class BudgetService:
    
    @staticmethod
    def create_budget(db: Session, budget_create: BudgetCreate, user_id: uuid.UUID) -> Budget:
        """Create a new budget"""
        budget = Budget(
            user_id=user_id,
            **budget_create.model_dump()
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return budget
    
    @staticmethod
    def get_budget(db: Session, budget_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Budget]:
        """Get a budget by ID"""
        return db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == user_id
        ).first()
    
    @staticmethod
    def get_budgets(
        db: Session, 
        user_id: uuid.UUID, 
        filters: Optional[BudgetFilter] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Budget]:
        """Get budgets with optional filters"""
        query = db.query(Budget).filter(Budget.user_id == user_id)
        
        if filters:
            if filters.category_id:
                query = query.filter(Budget.category_id == filters.category_id)
            if filters.period:
                query = query.filter(Budget.period == filters.period.value)
            if filters.is_active is not None:
                query = query.filter(Budget.is_active == filters.is_active)
            if filters.start_date:
                query = query.filter(Budget.start_date >= filters.start_date)
            if filters.end_date:
                query = query.filter(
                    or_(Budget.end_date.is_(None), Budget.end_date <= filters.end_date)
                )
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_budget(
        db: Session, 
        budget: Budget, 
        budget_update: BudgetUpdate
    ) -> Budget:
        """Update a budget"""
        update_data = budget_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)
        
        budget.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(budget)
        return budget
    
    @staticmethod
    def delete_budget(db: Session, budget: Budget) -> bool:
        """Delete a budget"""
        db.delete(budget)
        db.commit()
        return True
    
    @staticmethod
    def calculate_budget_usage(
        db: Session, 
        budget: Budget, 
        current_date: Optional[date] = None
    ) -> BudgetUsage:
        """Calculate current budget usage"""
        if not current_date:
            current_date = date.today()
        
        # Calculate period boundaries
        period_start, period_end = BudgetService._get_period_boundaries(
            budget, current_date
        )
        
        # Get total spent in this period
        spent_query = db.query(func.coalesce(func.sum(func.abs(Transaction.amount_cents)), 0))
        spent_query = spent_query.filter(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
            Transaction.amount_cents < 0  # Only expenses
        )
        
        # Filter by category if specified
        if budget.category_id:
            spent_query = spent_query.filter(Transaction.category_id == budget.category_id)
        
        spent_cents = spent_query.scalar() or 0
        remaining_cents = budget.amount_cents - spent_cents
        percentage_used = (spent_cents / budget.amount_cents) * 100 if budget.amount_cents > 0 else 0
        
        # Calculate days remaining in period
        days_remaining = (period_end - current_date).days if period_end > current_date else 0
        
        return BudgetUsage(
            budget_id=str(budget.id),
            spent_cents=spent_cents,
            remaining_cents=remaining_cents,
            percentage_used=round(percentage_used, 2),
            is_over_budget=spent_cents > budget.amount_cents,
            days_remaining=days_remaining
        )
    
    @staticmethod
    def get_budget_alerts(db: Session, user_id: uuid.UUID) -> List[BudgetAlert]:
        """Get active budget alerts for a user"""
        alerts = []
        budgets = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.is_active == True
        ).all()
        
        for budget in budgets:
            usage = BudgetService.calculate_budget_usage(db, budget)
            category_name = None
            
            if budget.category_id:
                category = db.query(Category).filter(Category.id == budget.category_id).first()
                category_name = category.name if category else None
            
            # Check for alerts
            alert_threshold_percentage = budget.alert_threshold * 100
            
            if usage.percentage_used >= alert_threshold_percentage:
                alert_type = "exceeded" if usage.is_over_budget else "warning"
                message = BudgetService._generate_alert_message(budget, usage, alert_type)
                
                alerts.append(BudgetAlert(
                    budget_id=str(budget.id),
                    budget_name=budget.name,
                    category_name=category_name,
                    alert_type=alert_type,
                    message=message,
                    percentage_used=usage.percentage_used,
                    amount_over=max(0, usage.spent_cents - budget.amount_cents) if usage.is_over_budget else None
                ))
            
            # Check for near end of period alerts
            if usage.days_remaining and usage.days_remaining <= 3 and usage.percentage_used < 50:
                alerts.append(BudgetAlert(
                    budget_id=str(budget.id),
                    budget_name=budget.name,
                    category_name=category_name,
                    alert_type="near_end",
                    message=f"Budget period ending in {usage.days_remaining} days with {usage.percentage_used:.1f}% used",
                    percentage_used=usage.percentage_used
                ))
        
        return alerts
    
    @staticmethod
    def get_budget_summary(db: Session, user_id: uuid.UUID) -> BudgetSummary:
        """Get budget summary statistics"""
        budgets = db.query(Budget).filter(Budget.user_id == user_id).all()
        active_budgets = [b for b in budgets if b.is_active]
        
        total_budgeted_cents = sum(b.amount_cents for b in active_budgets)
        total_spent_cents = 0
        over_budget_count = 0
        
        # Calculate totals from usage
        for budget in active_budgets:
            usage = BudgetService.calculate_budget_usage(db, budget)
            total_spent_cents += usage.spent_cents
            if usage.is_over_budget:
                over_budget_count += 1
        
        total_remaining_cents = total_budgeted_cents - total_spent_cents
        alerts = BudgetService.get_budget_alerts(db, user_id)
        
        return BudgetSummary(
            total_budgets=len(budgets),
            active_budgets=len(active_budgets),
            total_budgeted_cents=total_budgeted_cents,
            total_spent_cents=total_spent_cents,
            total_remaining_cents=total_remaining_cents,
            over_budget_count=over_budget_count,
            alert_count=len(alerts)
        )
    
    @staticmethod
    def get_budget_progress(
        db: Session, 
        budget_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[BudgetProgress]:
        """Get detailed budget progress over time"""
        budget = BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return None
        
        # Get current period boundaries
        period_start, period_end = BudgetService._get_period_boundaries(budget, date.today())
        
        # Get daily spending data
        daily_spending = BudgetService._get_spending_by_timeframe(
            db, budget, period_start, period_end, 'day'
        )
        
        # Get weekly spending data
        weekly_spending = BudgetService._get_spending_by_timeframe(
            db, budget, period_start, period_end, 'week'
        )
        
        # Get category breakdown if this is a general budget
        category_breakdown = []
        if not budget.category_id:
            category_breakdown = BudgetService._get_category_breakdown(
                db, budget, period_start, period_end
            )
        
        return BudgetProgress(
            budget_id=str(budget.id),
            budget_name=budget.name,
            period_start=period_start,
            period_end=period_end,
            daily_spending=daily_spending,
            weekly_spending=weekly_spending,
            category_breakdown=category_breakdown
        )
    
    @staticmethod
    def _get_period_boundaries(budget: Budget, current_date: date) -> Tuple[date, date]:
        """Calculate period start and end dates based on budget period"""
        if budget.period == BudgetPeriod.WEEKLY:
            # Start of current week (Monday)
            days_since_monday = current_date.weekday()
            period_start = current_date - timedelta(days=days_since_monday)
            period_end = period_start + timedelta(days=6)
            
        elif budget.period == BudgetPeriod.MONTHLY:
            # Start of current month
            period_start = current_date.replace(day=1)
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            period_end = next_month - timedelta(days=1)
            
        elif budget.period == BudgetPeriod.QUARTERLY:
            # Start of current quarter
            quarter_start_month = ((current_date.month - 1) // 3) * 3 + 1
            period_start = current_date.replace(month=quarter_start_month, day=1)
            quarter_end_month = quarter_start_month + 2
            if quarter_end_month > 12:
                period_end = current_date.replace(year=current_date.year + 1, month=quarter_end_month - 12, day=1)
            else:
                period_end = current_date.replace(month=quarter_end_month + 1, day=1)
            period_end = period_end - timedelta(days=1)
            
        else:  # YEARLY
            # Start of current year
            period_start = current_date.replace(month=1, day=1)
            period_end = current_date.replace(month=12, day=31)
        
        # Apply budget-specific start/end date constraints
        if budget.start_date and period_start < budget.start_date:
            period_start = budget.start_date
        if budget.end_date and period_end > budget.end_date:
            period_end = budget.end_date
        
        return period_start, period_end
    
    @staticmethod
    def _get_spending_by_timeframe(
        db: Session, 
        budget: Budget, 
        period_start: date, 
        period_end: date, 
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get spending data grouped by timeframe"""
        query = db.query(Transaction).filter(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
            Transaction.amount_cents < 0  # Only expenses
        )
        
        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)
        
        transactions = query.all()
        
        # Group by timeframe
        grouped_data = {}
        for transaction in transactions:
            if timeframe == 'day':
                key = transaction.transaction_date.isoformat()
            elif timeframe == 'week':
                # Get start of week
                days_since_monday = transaction.transaction_date.weekday()
                week_start = transaction.transaction_date - timedelta(days=days_since_monday)
                key = week_start.isoformat()
            
            if key not in grouped_data:
                grouped_data[key] = 0
            grouped_data[key] += abs(transaction.amount_cents)
        
        # Convert to list format
        result = []
        for key, amount in grouped_data.items():
            result.append({
                'date' if timeframe == 'day' else 'week': key,
                'amount_cents': amount
            })
        
        return sorted(result, key=lambda x: x['date' if timeframe == 'day' else 'week'])
    
    @staticmethod
    def _get_category_breakdown(
        db: Session, 
        budget: Budget, 
        period_start: date, 
        period_end: date
    ) -> List[Dict[str, Any]]:
        """Get spending breakdown by category"""
        query = db.query(
            Category.name,
            func.sum(func.abs(Transaction.amount_cents)).label('total_amount')
        ).select_from(Transaction).join(Category).filter(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
            Transaction.amount_cents < 0  # Only expenses
        ).group_by(Category.name)
        
        results = query.all()
        total_spent = sum(result.total_amount for result in results)
        
        breakdown = []
        for result in results:
            percentage = (result.total_amount / total_spent * 100) if total_spent > 0 else 0
            breakdown.append({
                'category': result.name,
                'amount_cents': int(result.total_amount),
                'percentage': round(percentage, 2)
            })
        
        return sorted(breakdown, key=lambda x: x['amount_cents'], reverse=True)
    
    @staticmethod
    def _generate_alert_message(budget: Budget, usage: BudgetUsage, alert_type: str) -> str:
        """Generate alert message based on budget and usage"""
        amount_dollars = budget.amount_cents / 100
        spent_dollars = usage.spent_cents / 100
        
        if alert_type == "exceeded":
            over_amount = (usage.spent_cents - budget.amount_cents) / 100
            return f"Budget '{budget.name}' exceeded by ${over_amount:.2f}! You've spent ${spent_dollars:.2f} of ${amount_dollars:.2f}"
        elif alert_type == "warning":
            return f"Budget '{budget.name}' is {usage.percentage_used:.1f}% used. You've spent ${spent_dollars:.2f} of ${amount_dollars:.2f}"
        
        return f"Budget alert for '{budget.name}'"