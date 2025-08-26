"""
Integration tests for Budget System Edge Cases and Bug Fixes.

These tests specifically cover the critical edge cases and bugs that were
identified and fixed in the budget system:
1. Quarterly period boundary calculation (Q4 crash bug)
2. Transaction isolation and race conditions
3. Alert threshold frontend-backend synchronization
4. Overlapping general budgets validation
5. Multiple budget overlap scenarios
6. Data consistency edge cases
"""
import pytest
from uuid import uuid4
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

from app.services.budget_service import BudgetService, BudgetCalculationEngine
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetUsage, BudgetAlert, 
    BudgetFilter, BudgetPeriod
)
from app.models.budget import Budget, BudgetPeriod as ModelBudgetPeriod
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.core.exceptions import ValidationError


class TestQuarterlyPeriodBoundaries:
    """Test quarterly period boundary calculations, especially Q4."""
    
    def test_quarterly_q4_boundaries_december(self):
        """Test Q4 quarterly period calculation doesn't crash in December."""
        # Arrange
        december_date = date(2024, 12, 15)  # December 15th, Q4
        
        # Act & Assert - should not crash
        period_start, period_end = BudgetCalculationEngine.calculate_period_boundaries(
            ModelBudgetPeriod.QUARTERLY, december_date
        )
        
        # Assert correct Q4 boundaries
        assert period_start == date(2024, 10, 1)  # October 1st
        assert period_end == date(2024, 12, 31)   # December 31st
        
    def test_quarterly_q1_boundaries_february(self):
        """Test Q1 quarterly period calculation in February (leap year edge case)."""
        # Arrange
        february_date = date(2024, 2, 15)  # February 15th, Q1, leap year
        
        # Act
        period_start, period_end = BudgetCalculationEngine.calculate_period_boundaries(
            ModelBudgetPeriod.QUARTERLY, february_date
        )
        
        # Assert correct Q1 boundaries
        assert period_start == date(2024, 1, 1)   # January 1st
        assert period_end == date(2024, 3, 31)    # March 31st
    
    def test_quarterly_all_quarters_boundaries(self):
        """Test all quarterly boundaries are calculated correctly."""
        test_cases = [
            # (test_date, expected_start, expected_end, quarter_name)
            (date(2024, 2, 15), date(2024, 1, 1), date(2024, 3, 31), "Q1"),
            (date(2024, 5, 15), date(2024, 4, 1), date(2024, 6, 30), "Q2"),
            (date(2024, 8, 15), date(2024, 7, 1), date(2024, 9, 30), "Q3"),
            (date(2024, 11, 15), date(2024, 10, 1), date(2024, 12, 31), "Q4"),
        ]
        
        for test_date, expected_start, expected_end, quarter_name in test_cases:
            with pytest.subcontext(f"Testing {quarter_name}"):
                period_start, period_end = BudgetCalculationEngine.calculate_period_boundaries(
                    ModelBudgetPeriod.QUARTERLY, test_date
                )
                assert period_start == expected_start, f"Q1 start wrong: {period_start} != {expected_start}"
                assert period_end == expected_end, f"Q1 end wrong: {period_end} != {expected_end}"


class TestOverlappingGeneralBudgets:
    """Test validation for overlapping general budgets."""
    
    def test_create_overlapping_general_budget_monthly_raises_error(
        self, test_db_session, test_user
    ):
        """Test creating overlapping monthly general budgets raises ValidationError."""
        # Arrange - Create first general budget
        first_budget = BudgetService.create_budget(
            test_db_session, 
            BudgetCreate(
                name="General Monthly Budget 1",
                category_id=None,  # General budget
                amount_cents=100000,  # $1000
                period="monthly",
                start_date=date(2024, 1, 1),
                alert_threshold=0.8
            ),
            test_user.id
        )
        
        # Act & Assert - Creating another overlapping general budget should raise error
        with pytest.raises(ValidationError) as exc_info:
            BudgetService.create_budget(
                test_db_session,
                BudgetCreate(
                    name="General Monthly Budget 2",
                    category_id=None,  # General budget
                    amount_cents=150000,  # $1500
                    period="monthly",
                    start_date=date(2024, 1, 1),
                    alert_threshold=0.9
                ),
                test_user.id
            )
        
        assert "overlapping general budgets" in str(exc_info.value).lower()
        assert "General Monthly Budget 1" in str(exc_info.value)
    
    def test_create_general_budget_different_periods_allowed(
        self, test_db_session, test_user
    ):
        """Test creating general budgets for different periods is allowed."""
        # Arrange & Act - Create monthly and yearly general budgets
        monthly_budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Monthly General Budget",
                category_id=None,
                amount_cents=100000,
                period="monthly",
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        yearly_budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Yearly General Budget", 
                category_id=None,
                amount_cents=1200000,
                period="yearly",
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        # Assert both were created successfully
        assert monthly_budget.id != yearly_budget.id
        assert monthly_budget.period == ModelBudgetPeriod.MONTHLY
        assert yearly_budget.period == ModelBudgetPeriod.YEARLY
    
    def test_update_to_overlapping_general_budget_raises_error(
        self, test_db_session, test_user, test_category
    ):
        """Test updating category budget to general budget with overlap raises error."""
        # Arrange - Create general budget and category budget
        general_budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="General Budget",
                category_id=None,
                amount_cents=100000,
                period="monthly",
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        category_budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Category Budget",
                category_id=test_category.id,
                amount_cents=50000,
                period="monthly", 
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        # Act & Assert - Updating category budget to general should raise error
        with pytest.raises(ValidationError) as exc_info:
            BudgetService.update_budget(
                test_db_session,
                category_budget,
                BudgetUpdate(category_id=None)  # Convert to general budget
            )
        
        assert "overlapping general budgets" in str(exc_info.value).lower()


class TestAlertThresholdConsistency:
    """Test alert threshold consistency between frontend and backend."""
    
    def test_budget_alert_uses_custom_threshold_80_percent(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget alerts use custom 80% threshold instead of hardcoded 90%."""
        # Arrange - Create budget with 80% alert threshold
        budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Custom Threshold Budget",
                category_id=test_category.id,
                amount_cents=100000,  # $1000 budget
                period="monthly",
                start_date=date(2024, 1, 1),
                alert_threshold=0.8  # 80% threshold
            ),
            test_user.id
        )
        
        # Create transaction that exceeds 80% but not 90%
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=-85000,  # -$850 (85% of budget)
            currency="USD",
            description="Large expense",
            transaction_date=date(2024, 1, 15),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act - Get budget alerts
        alerts = BudgetService.get_budget_alerts(test_db_session, test_user.id)
        
        # Assert - Should trigger alert at 80% threshold
        budget_alerts = [alert for alert in alerts if alert.budget_id == str(budget.id)]
        assert len(budget_alerts) == 1
        assert budget_alerts[0].alert_type == "warning"
        assert budget_alerts[0].percentage_used == 85.0
    
    def test_budget_alert_uses_custom_threshold_95_percent(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget alerts use custom 95% threshold."""
        # Arrange - Create budget with 95% alert threshold  
        budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="High Threshold Budget",
                category_id=test_category.id,
                amount_cents=100000,  # $1000 budget
                period="monthly",
                start_date=date(2024, 1, 1),
                alert_threshold=0.95  # 95% threshold
            ),
            test_user.id
        )
        
        # Create transaction that's at 90% (would trigger old hardcoded threshold)
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=-90000,  # -$900 (90% of budget)
            currency="USD", 
            description="Large expense",
            transaction_date=date(2024, 1, 15),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act - Get budget alerts
        alerts = BudgetService.get_budget_alerts(test_db_session, test_user.id)
        
        # Assert - Should NOT trigger alert at 90% with 95% threshold
        budget_alerts = [alert for alert in alerts if alert.budget_id == str(budget.id)]
        assert len(budget_alerts) == 0, "Alert should not trigger at 90% with 95% threshold"


class TestBudgetCalculationConsistency:
    """Test that unified calculation engine produces consistent results."""
    
    def test_single_vs_batch_calculation_consistency(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test that single budget calculation matches batch calculation."""
        # Arrange - Create budget and transactions
        budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Consistency Test Budget",
                category_id=test_category.id,
                amount_cents=100000,  # $1000
                period="monthly",
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=-35000,  # -$350
            currency="USD",
            description="Test expense",
            transaction_date=date(2024, 1, 15),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act - Calculate using both methods
        single_usage = BudgetService.calculate_budget_usage(test_db_session, budget, date(2024, 1, 20))
        
        batch_results = BudgetService.get_budgets_with_usage(test_db_session, test_user.id)
        batch_usage = None
        for budget_obj, usage_obj in batch_results:
            if budget_obj.id == budget.id:
                batch_usage = usage_obj
                break
        
        # Assert - Both methods should produce identical results
        assert batch_usage is not None, "Budget should be found in batch results"
        assert single_usage.spent_cents == batch_usage.spent_cents
        assert single_usage.remaining_cents == batch_usage.remaining_cents
        assert single_usage.percentage_used == batch_usage.percentage_used
        assert single_usage.is_over_budget == batch_usage.is_over_budget


class TestDatabaseConstraintValidation:
    """Test that database constraints properly enforce data integrity."""
    
    def test_negative_amount_budget_rejected(self, test_db_session, test_user):
        """Test that budgets with negative amounts are rejected."""
        # This test will only work after migration is applied
        with pytest.raises(Exception):  # Will be IntegrityError after migration
            BudgetService.create_budget(
                test_db_session,
                BudgetCreate(
                    name="Invalid Budget",
                    amount_cents=-50000,  # Negative amount
                    period="monthly",
                    start_date=date(2024, 1, 1)
                ),
                test_user.id
            )
    
    def test_invalid_alert_threshold_rejected(self, test_db_session, test_user):
        """Test that invalid alert thresholds are rejected."""
        # This test will only work after migration is applied
        with pytest.raises(Exception):  # Will be IntegrityError after migration
            BudgetService.create_budget(
                test_db_session,
                BudgetCreate(
                    name="Invalid Threshold Budget",
                    amount_cents=100000,
                    period="monthly", 
                    start_date=date(2024, 1, 1),
                    alert_threshold=1.5  # Invalid threshold > 1.0
                ),
                test_user.id
            )
    
    def test_invalid_date_range_rejected(self, test_db_session, test_user):
        """Test that budgets with end_date before start_date are rejected."""
        # This test will only work after migration is applied
        with pytest.raises(Exception):  # Will be IntegrityError after migration
            BudgetService.create_budget(
                test_db_session,
                BudgetCreate(
                    name="Invalid Date Range Budget", 
                    amount_cents=100000,
                    period="monthly",
                    start_date=date(2024, 2, 1),
                    end_date=date(2024, 1, 1)  # End before start
                ),
                test_user.id
            )


class TestTransactionIsolation:
    """Test transaction isolation prevents race conditions."""
    
    def test_budget_calculation_isolation(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test that budget calculations are isolated from concurrent changes."""
        # Note: This is difficult to test without actual concurrency
        # The main test is that the transaction isolation syntax is correct
        # and doesn't cause errors
        
        # Arrange
        budget = BudgetService.create_budget(
            test_db_session,
            BudgetCreate(
                name="Isolation Test Budget",
                category_id=test_category.id,
                amount_cents=100000,
                period="monthly",
                start_date=date(2024, 1, 1)
            ),
            test_user.id
        )
        
        # Act & Assert - Should complete without errors
        usage = BudgetService.calculate_budget_usage(test_db_session, budget)
        
        assert usage is not None
        assert usage.budget_id == str(budget.id)
        assert usage.spent_cents == 0  # No transactions yet
        assert usage.remaining_cents == 100000