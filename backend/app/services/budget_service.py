from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session, joinedload
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
    BudgetPeriod, BudgetCalendarDay, BudgetCalendarResponse
)
from .notification_service import NotificationService


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
        return db.query(Budget).options(
            joinedload(Budget.category)
        ).filter(
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
        # Use eager loading to prevent N+1 queries when accessing category
        query = db.query(Budget).options(
            joinedload(Budget.category)
        ).filter(Budget.user_id == user_id)
        
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
    def get_budgets_with_usage(
        db: Session, 
        user_id: uuid.UUID, 
        filters: Optional[BudgetFilter] = None,
        skip: int = 0,
        limit: int = 100,
        current_date: Optional[date] = None
    ) -> List[Tuple[Budget, BudgetUsage]]:
        """Get budgets with their usage data calculated efficiently to avoid N+1 queries
        
        Returns:
            List of tuples containing (Budget object, BudgetUsage object)
        """
        # First get the basic budgets with eager loading
        budgets = BudgetService.get_budgets(db, user_id, filters, skip, limit)
        
        if not budgets:
            return []
        
        # Extract budget IDs for the aggregated query
        budget_ids = [budget.id for budget in budgets]
        
        # Get optimized spending data for just these budgets
        # Note: only_active is handled by the initial get_budgets call, so we don't filter here
        budget_data = BudgetService._get_budget_spending_data(
            db=db, 
            user_id=user_id, 
            current_date=current_date,
            budget_ids=budget_ids,
            only_active=False  # Don't filter here since get_budgets already applied filters
        )
        
        # Create a lookup dictionary for O(1) access
        usage_lookup = {data['budget_id']: data for data in budget_data}
        
        # Combine budget objects with their usage data
        results = []
        for budget in budgets:
            usage_data = usage_lookup.get(budget.id)
            if usage_data:
                # Create BudgetUsage object from the optimized data
                usage = BudgetUsage(
                    budget_id=str(usage_data['budget_id']),
                    spent_cents=usage_data['spent_cents'],
                    remaining_cents=usage_data['remaining_cents'],
                    percentage_used=usage_data['percentage_used'],
                    is_over_budget=usage_data['is_over_budget'],
                    days_remaining=usage_data['days_remaining']
                )
            else:
                # Fallback to zero usage if no data found
                usage = BudgetUsage(
                    budget_id=str(budget.id),
                    spent_cents=0,
                    remaining_cents=budget.amount_cents,
                    percentage_used=0.0,
                    is_over_budget=False,
                    days_remaining=None
                )
            
            # Apply over_budget filter if specified
            if filters and filters.over_budget is not None:
                if usage.is_over_budget != filters.over_budget:
                    continue
            
            results.append((budget, usage))
        
        return results
    
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
        
        # If current date is before budget start date, return zero usage
        if current_date < budget.start_date:
            return BudgetUsage(
                budget_id=str(budget.id),
                spent_cents=0,
                remaining_cents=budget.amount_cents,
                percentage_used=0.0,
                is_over_budget=False,
                days_remaining=None
            )
        
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
    def _get_budget_spending_data(
        db: Session, 
        user_id: uuid.UUID, 
        current_date: Optional[date] = None,
        budget_ids: Optional[List[uuid.UUID]] = None,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """Get budget spending data optimized to avoid N+1 pattern using a single aggregated query
        
        Args:
            db: Database session
            user_id: User UUID
            current_date: Date for calculations (defaults to today)
            budget_ids: Optional list of specific budget IDs to fetch
            only_active: Whether to filter only active budgets (defaults to True)
        """
        if not current_date:
            current_date = date.today()
            
        # First, get budgets with their metadata
        budgets_query = (
            db.query(
                Budget.id,
                Budget.name,
                Budget.amount_cents,
                Budget.period,
                Budget.start_date,
                Budget.end_date,
                Budget.category_id,
                Category.name.label('category_name')
            )
            .outerjoin(Category, Category.id == Budget.category_id)
            .filter(Budget.user_id == user_id)
        )
        
        # Apply filtering
        if only_active:
            budgets_query = budgets_query.filter(Budget.is_active == True)
        
        if budget_ids:
            budgets_query = budgets_query.filter(Budget.id.in_(budget_ids))
        
        budget_results = budgets_query.all()
        
        if not budget_results:
            return []
        
        # Calculate period boundaries for all budgets and group by similar periods for batch processing
        budget_periods = {}
        budget_metadata = {}
        
        for result in budget_results:
            budget_obj = Budget(
                id=result.id,
                period=result.period,
                start_date=result.start_date,
                end_date=result.end_date
            )
            period_start, period_end = BudgetService._get_period_boundaries(budget_obj, current_date)
            
            # Store metadata for each budget
            budget_metadata[result.id] = {
                'budget_id': result.id,
                'budget_name': result.name,
                'amount_cents': result.amount_cents,
                'category_id': result.category_id,
                'category_name': result.category_name,
                'period_start': period_start,
                'period_end': period_end
            }
            
            # Group budgets by their period boundaries for efficient querying
            period_key = (period_start, period_end)
            if period_key not in budget_periods:
                budget_periods[period_key] = []
            budget_periods[period_key].append(result)
        
        # Now get spending data for each period group in batch queries
        spending_by_budget = {}
        
        for (period_start, period_end), budgets_in_period in budget_periods.items():
            # Get spending for all budgets in this period with a single query
            budget_ids = [b.id for b in budgets_in_period]
            category_ids = [b.category_id for b in budgets_in_period if b.category_id]
            
            # Query for category-specific budgets
            if category_ids:
                category_spending_query = (
                    db.query(
                        Budget.id.label('budget_id'),
                        func.coalesce(func.sum(func.abs(Transaction.amount_cents)), 0).label('spent_cents')
                    )
                    .select_from(Budget)
                    .outerjoin(Transaction, and_(
                        Transaction.user_id == user_id,
                        Transaction.category_id == Budget.category_id,
                        Transaction.transaction_date >= period_start,
                        Transaction.transaction_date <= period_end,
                        Transaction.amount_cents < 0  # Only expenses
                    ))
                    .filter(
                        Budget.id.in_(budget_ids),
                        Budget.category_id.isnot(None)
                    )
                    .group_by(Budget.id)
                )
                
                for result in category_spending_query.all():
                    spending_by_budget[result.budget_id] = result.spent_cents
            
            # Query for general budgets (no category filter)
            general_budget_ids = [b.id for b in budgets_in_period if not b.category_id]
            if general_budget_ids:
                # For general budgets, sum ALL expenses in the period
                general_spending_query = (
                    db.query(
                        func.coalesce(func.sum(func.abs(Transaction.amount_cents)), 0).label('total_spent')
                    )
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.transaction_date >= period_start,
                        Transaction.transaction_date <= period_end,
                        Transaction.amount_cents < 0  # Only expenses
                    )
                )
                
                total_spent = general_spending_query.scalar() or 0
                for budget_id in general_budget_ids:
                    spending_by_budget[budget_id] = total_spent
        
        # Combine metadata with spending data and calculate derived values
        budget_data = []
        for budget_id, metadata in budget_metadata.items():
            spent_cents = spending_by_budget.get(budget_id, 0)
            
            # Calculate derived values
            remaining_cents = metadata['amount_cents'] - spent_cents
            percentage_used = (spent_cents / metadata['amount_cents']) * 100 if metadata['amount_cents'] > 0 else 0
            is_over_budget = spent_cents > metadata['amount_cents']
            days_remaining = (metadata['period_end'] - current_date).days if metadata['period_end'] > current_date else 0
            
            budget_data.append({
                **metadata,
                'spent_cents': spent_cents,
                'remaining_cents': remaining_cents,
                'percentage_used': round(percentage_used, 2),
                'is_over_budget': is_over_budget,
                'days_remaining': days_remaining
            })
        
        return budget_data

    @staticmethod
    def get_budget_alerts(db: Session, user_id: uuid.UUID) -> List[BudgetAlert]:
        """Get active budget alerts for a user - optimized to avoid N+1 queries"""
        alerts = []
        
        # Get all budget spending data in optimized queries
        budget_data = BudgetService._get_budget_spending_data(db, user_id)
        
        for data in budget_data:
            # Check for alerts using hard-coded thresholds (90% warning, 100% exceeded)
            
            if data['percentage_used'] >= 100:
                alert_type = "exceeded"
            elif data['percentage_used'] >= 90:
                alert_type = "warning"
            else:
                continue  # No alert needed for this budget
            
            # Create a budget-like object for message generation
            budget_obj = Budget(
                id=data['budget_id'],
                name=data['budget_name'],
                amount_cents=data['amount_cents']
            )
            usage_obj = BudgetUsage(
                budget_id=str(data['budget_id']),
                spent_cents=data['spent_cents'],
                remaining_cents=data['remaining_cents'],
                percentage_used=data['percentage_used'],
                is_over_budget=data['is_over_budget'],
                days_remaining=data['days_remaining']
            )
            
            message = BudgetService._generate_alert_message(budget_obj, usage_obj, alert_type)
            
            alerts.append(BudgetAlert(
                budget_id=str(data['budget_id']),
                budget_name=data['budget_name'],
                category_name=data['category_name'],
                alert_type=alert_type,
                message=message,
                percentage_used=data['percentage_used'],
                amount_over=max(0, data['spent_cents'] - data['amount_cents']) if data['is_over_budget'] else None
            ))
            
            # Check for near end of period alerts
            if data['days_remaining'] and data['days_remaining'] <= 3 and data['percentage_used'] < 50:
                alerts.append(BudgetAlert(
                    budget_id=str(data['budget_id']),
                    budget_name=data['budget_name'],
                    category_name=data['category_name'],
                    alert_type="near_end",
                    message=f"Budget period ending in {data['days_remaining']} days with {data['percentage_used']:.1f}% used",
                    percentage_used=data['percentage_used']
                ))
        
        return alerts
    
    @staticmethod
    async def check_and_create_budget_notifications(db: Session, user_id: uuid.UUID) -> List[str]:
        """Check budgets and create persistent notifications for alerts - optimized to avoid N+1 queries"""
        created_notifications = []
        
        # Get optimized budget spending data
        budget_data = BudgetService._get_budget_spending_data(db, user_id)
        
        for data in budget_data:
            # Only create notifications for significant alerts (>= 90% or over budget)
            if data['percentage_used'] >= 90:
                try:
                    notification = await NotificationService.create_budget_alert(
                        db=db,
                        user_id=user_id,
                        budget_name=data['budget_name'],
                        current_amount_cents=data['spent_cents'],  # Keep as cents
                        budget_limit_cents=data['amount_cents'],  # Keep as cents
                        percentage_used=data['percentage_used'],
                        budget_id=data['budget_id']
                    )
                    created_notifications.append(str(notification.id))
                except Exception as e:
                    # Log error but continue with other budgets
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create budget notification for budget {data['budget_id']}: {e}")
        
        return created_notifications
    
    @staticmethod
    def get_budget_summary(db: Session, user_id: uuid.UUID) -> BudgetSummary:
        """Get budget summary statistics - optimized to avoid N+1 queries"""
        # Get all budgets count (including inactive)
        total_budgets_count = db.query(func.count(Budget.id)).filter(Budget.user_id == user_id).scalar()
        
        # Get optimized budget spending data for active budgets only
        budget_data = BudgetService._get_budget_spending_data(db, user_id)
        
        # Calculate totals from optimized data
        total_budgeted_cents = sum(data['amount_cents'] for data in budget_data)
        total_spent_cents = sum(data['spent_cents'] for data in budget_data)
        over_budget_count = sum(1 for data in budget_data if data['is_over_budget'])
        total_remaining_cents = total_budgeted_cents - total_spent_cents
        
        # Get alerts count (already optimized)
        alerts = BudgetService.get_budget_alerts(db, user_id)
        
        return BudgetSummary(
            total_budgets=total_budgets_count,
            active_budgets=len(budget_data),
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
    
    @staticmethod
    def get_budget_calendar(
        db: Session, 
        budget_id: uuid.UUID, 
        user_id: uuid.UUID,
        month: str  # YYYY-MM format
    ) -> Optional[BudgetCalendarResponse]:
        """Get budget calendar data for a specific month"""
        budget = BudgetService.get_budget(db, budget_id, user_id)
        if not budget:
            return None
        
        try:
            # Parse month
            year, month_num = map(int, month.split('-'))
            month_start = date(year, month_num, 1)
            
            # Calculate month end
            if month_num == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month_num + 1, 1) - timedelta(days=1)
            
        except (ValueError, IndexError):
            raise ValueError("Invalid month format. Use YYYY-MM")
        
        # Get budget period boundaries that overlap with requested month
        budget_period_start, budget_period_end = BudgetService._get_period_boundaries(budget, month_start)
        
        # Calculate daily spending limit
        total_days_in_period = (budget_period_end - budget_period_start).days + 1
        daily_limit_cents = budget.amount_cents // total_days_in_period
        
        # Get daily spending data for the month
        daily_data = []
        current_date = month_start
        
        while current_date <= month_end:
            # Check if this date is within the budget period
            if budget_period_start <= current_date <= budget_period_end:
                # Get spending for this day
                day_spending = BudgetService._get_daily_spending(
                    db, budget, current_date
                )
                
                percentage_used = (day_spending / daily_limit_cents * 100) if daily_limit_cents > 0 else 0
                
                # Get transaction count for this day
                transaction_count = BudgetService._get_daily_transaction_count(
                    db, budget, current_date
                )
                
                daily_data.append(BudgetCalendarDay(
                    date=current_date,
                    daily_spending_limit_cents=daily_limit_cents,
                    actual_spending_cents=day_spending,
                    percentage_used=round(percentage_used, 2),
                    is_over_limit=day_spending > daily_limit_cents,
                    transactions_count=transaction_count
                ))
            else:
                # Day is outside budget period
                daily_data.append(BudgetCalendarDay(
                    date=current_date,
                    daily_spending_limit_cents=0,
                    actual_spending_cents=0,
                    percentage_used=0.0,
                    is_over_limit=False,
                    transactions_count=0
                ))
            
            current_date += timedelta(days=1)
        
        # Calculate summary statistics
        total_days_with_limit = sum(1 for day in daily_data if day.daily_spending_limit_cents > 0)
        total_spending = sum(day.actual_spending_cents for day in daily_data)
        total_limit = sum(day.daily_spending_limit_cents for day in daily_data)
        days_over_limit = sum(1 for day in daily_data if day.is_over_limit)
        avg_daily_spending = total_spending / max(total_days_with_limit, 1)
        
        summary = {
            "total_spending_cents": total_spending,
            "total_limit_cents": total_limit,
            "days_in_month": len(daily_data),
            "days_with_budget": total_days_with_limit,
            "days_over_limit": days_over_limit,
            "average_daily_spending_cents": round(avg_daily_spending),
            "month_progress_percentage": round((total_spending / total_limit * 100) if total_limit > 0 else 0, 2)
        }
        
        return BudgetCalendarResponse(
            budget_id=str(budget.id),
            budget_name=budget.name,
            month=month,
            period_start=budget_period_start,
            period_end=budget_period_end,
            daily_data=daily_data,
            summary=summary
        )
    
    @staticmethod
    def _get_daily_spending(
        db: Session, 
        budget: Budget, 
        target_date: date
    ) -> int:
        """Get total spending for a specific day"""
        query = db.query(func.coalesce(func.sum(func.abs(Transaction.amount_cents)), 0))
        query = query.filter(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_date == target_date,
            Transaction.amount_cents < 0  # Only expenses
        )
        
        # Filter by category if budget is category-specific
        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)
        
        return query.scalar() or 0
    
    @staticmethod
    def _get_daily_transaction_count(
        db: Session, 
        budget: Budget, 
        target_date: date
    ) -> int:
        """Get transaction count for a specific day"""
        query = db.query(func.count(Transaction.id))
        query = query.filter(
            Transaction.user_id == budget.user_id,
            Transaction.transaction_date == target_date,
            Transaction.amount_cents < 0  # Only expenses
        )
        
        # Filter by category if budget is category-specific
        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)
        
        return query.scalar() or 0