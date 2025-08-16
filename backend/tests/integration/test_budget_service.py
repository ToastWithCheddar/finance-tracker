"""
Integration tests for BudgetService.

These tests verify that BudgetService works correctly with a real database
and test the complete workflow including data persistence and retrieval.
"""
import pytest
from uuid import uuid4
from datetime import date, datetime, timezone, timedelta

from app.services.budget_service import BudgetService
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetUsage, BudgetAlert, 
    BudgetFilter, BudgetPeriod
)
from app.models.budget import Budget
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


class TestBudgetServiceCreateBudgetIntegration:
    """Integration tests for budget creation with real database."""
    
    def test_create_budget_integration_success(
        self, test_db_session, test_user, test_category
    ):
        """Test complete budget creation flow with database."""
        # Arrange
        budget_data = BudgetCreate(
            name="Monthly Groceries",
            category_id=test_category.id,
            amount_cents=50000,  # $500.00
            period="monthly",
            start_date=date.today(),
            end_date=date.today().replace(month=date.today().month % 12 + 1),
            alert_threshold=0.8,
            is_active=True
        )
        
        # Act
        result = BudgetService.create_budget(test_db_session, budget_data, test_user.id)
        
        # Assert
        assert result is not None
        assert result.id is not None
        assert result.user_id == test_user.id
        assert result.name == "Monthly Groceries"
        assert result.category_id == test_category.id
        assert result.amount_cents == 50000
        assert result.period == "monthly"
        assert result.alert_threshold == 0.8
        assert result.is_active is True
        assert result.created_at is not None
        
        # Verify data was actually persisted
        retrieved = test_db_session.query(Budget).filter(
            Budget.id == result.id
        ).first()
        assert retrieved is not None
        assert retrieved.user_id == test_user.id
        assert retrieved.name == "Monthly Groceries"

    def test_create_budget_without_category_integration(
        self, test_db_session, test_user
    ):
        """Test budget creation without specific category (overall budget)."""
        # Arrange
        budget_data = BudgetCreate(
            name="Overall Monthly Budget",
            category_id=None,  # No specific category
            amount_cents=200000,  # $2000.00
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.9,
            is_active=True
        )
        
        # Act
        result = BudgetService.create_budget(test_db_session, budget_data, test_user.id)
        
        # Assert
        assert result is not None
        assert result.category_id is None
        assert result.name == "Overall Monthly Budget"
        assert result.amount_cents == 200000
        
        # Verify persistence
        retrieved = test_db_session.query(Budget).filter(
            Budget.id == result.id
        ).first()
        assert retrieved is not None
        assert retrieved.category_id is None


class TestBudgetServiceReadOperationsIntegration:
    """Integration tests for budget read operations."""
    
    def test_get_budget_integration(self, test_db_session, test_user, test_category):
        """Test budget retrieval with real database and eager loading."""
        # Arrange - Create a budget directly in the database
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            name="Integration Test Budget",
            amount_cents=75000,  # $750.00
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.8,
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        test_db_session.refresh(budget)
        
        # Act
        result = BudgetService.get_budget(test_db_session, budget.id, test_user.id)
        
        # Assert
        assert result is not None
        assert result.id == budget.id
        assert result.user_id == test_user.id
        assert result.name == "Integration Test Budget"
        assert result.amount_cents == 75000
        
        # Verify eager loading worked (category should be loaded)
        assert result.category is not None
        assert result.category.id == test_category.id
        assert result.category.name == test_category.name

    def test_get_budget_user_isolation(self, test_db_session, test_category):
        """Test that users can only access their own budgets."""
        # Arrange - Create two users
        user1 = User(
            id=uuid4(),
            email="user1@example.com",
            display_name="User 1",
            locale="en-US",
            timezone="UTC",
            currency="USD",
            is_active=True
        )
        user2 = User(
            id=uuid4(),
            email="user2@example.com",
            display_name="User 2",
            locale="en-US",
            timezone="UTC",
            currency="USD",
            is_active=True
        )
        test_db_session.add(user1)
        test_db_session.add(user2)
        test_db_session.commit()
        
        # Create budget for user1
        budget = Budget(
            id=uuid4(),
            user_id=user1.id,
            name="User 1 Budget",
            amount_cents=30000,
            period="monthly",
            start_date=date.today(),
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Act - User1 should be able to access their budget
        result1 = BudgetService.get_budget(test_db_session, budget.id, user1.id)
        
        # Act - User2 should NOT be able to access user1's budget
        result2 = BudgetService.get_budget(test_db_session, budget.id, user2.id)
        
        # Assert
        assert result1 is not None
        assert result1.user_id == user1.id
        assert result2 is None  # User2 should not see user1's budget

    def test_get_budgets_with_filters_integration(
        self, test_db_session, test_user, test_category
    ):
        """Test budget filtering with real database."""
        # Arrange - Create another category for testing
        category2 = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Entertainment",
            description="Entertainment expenses",
            is_system=False,
            is_active=True,
            sort_order=2
        )
        test_db_session.add(category2)
        test_db_session.commit()
        
        # Create multiple budgets
        budgets = []
        budget_configs = [
            ("Groceries Budget", test_category.id, "monthly", True),
            ("Entertainment Budget", category2.id, "monthly", True),
            ("Weekly Allowance", None, "weekly", False),  # Inactive budget
            ("Annual Savings", None, "yearly", True),
        ]
        
        for i, (name, category_id, period, is_active) in enumerate(budget_configs):
            budget = Budget(
                id=uuid4(),
                user_id=test_user.id,
                category_id=category_id,
                name=name,
                amount_cents=(i + 1) * 10000,  # $100, $200, $300, $400
                period=period,
                start_date=date.today(),
                is_active=is_active
            )
            budgets.append(budget)
            test_db_session.add(budget)
        
        test_db_session.commit()
        
        # Act - Filter by category
        filters = BudgetFilter(
            category_id=str(test_category.id),
            is_active=True
        )
        
        result = BudgetService.get_budgets(test_db_session, test_user.id, filters, skip=0, limit=100)
        
        # Assert
        assert len(result) == 1  # Only groceries budget should match
        assert result[0].name == "Groceries Budget"
        assert result[0].category_id == test_category.id
        assert result[0].is_active is True

    def test_get_budgets_pagination_integration(
        self, test_db_session, test_user
    ):
        """Test budget pagination with real database."""
        # Arrange - Create 5 budgets
        for i in range(5):
            budget = Budget(
                id=uuid4(),
                user_id=test_user.id,
                name=f"Budget {i + 1}",
                amount_cents=(i + 1) * 10000,
                period="monthly",
                start_date=date.today(),
                is_active=True
            )
            test_db_session.add(budget)
        
        test_db_session.commit()
        
        # Act - Get first 2 budgets
        result_page1 = BudgetService.get_budgets(
            test_db_session, test_user.id, filters=None, skip=0, limit=2
        )
        
        # Act - Get next 2 budgets
        result_page2 = BudgetService.get_budgets(
            test_db_session, test_user.id, filters=None, skip=2, limit=2
        )
        
        # Assert
        assert len(result_page1) == 2
        assert len(result_page2) == 2
        
        # Ensure different budgets on different pages
        page1_ids = {b.id for b in result_page1}
        page2_ids = {b.id for b in result_page2}
        assert page1_ids.isdisjoint(page2_ids)  # No overlap


class TestBudgetServiceUpdateIntegration:
    """Integration tests for budget updates."""
    
    def test_update_budget_integration(self, test_db_session, test_user, test_category):
        """Test budget update with real database."""
        # Arrange - Create initial budget
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            name="Original Budget Name",
            amount_cents=30000,
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.8,
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        test_db_session.refresh(budget)
        
        # Act - Update the budget
        update_data = BudgetUpdate(
            name="Updated Budget Name",
            amount_cents=40000,
            alert_threshold=0.9,
            is_active=False
        )
        
        result = BudgetService.update_budget(test_db_session, budget, update_data)
        
        # Assert
        assert result.name == "Updated Budget Name"
        assert result.amount_cents == 40000
        assert result.alert_threshold == 0.9
        assert result.is_active is False
        assert result.updated_at is not None
        
        # Verify changes were persisted
        retrieved = test_db_session.query(Budget).filter(
            Budget.id == budget.id
        ).first()
        assert retrieved.name == "Updated Budget Name"
        assert retrieved.amount_cents == 40000
        assert retrieved.alert_threshold == 0.9
        assert retrieved.is_active is False

    def test_update_budget_partial_integration(self, test_db_session, test_user):
        """Test partial budget update (only some fields)."""
        # Arrange
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            name="Partial Update Test",
            amount_cents=25000,
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.75,
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        test_db_session.refresh(budget)
        
        # Act - Update only the amount
        update_data = BudgetUpdate(amount_cents=35000)
        
        result = BudgetService.update_budget(test_db_session, budget, update_data)
        
        # Assert
        assert result.amount_cents == 35000  # Updated
        assert result.name == "Partial Update Test"  # Unchanged
        assert result.alert_threshold == 0.75  # Unchanged
        assert result.is_active is True  # Unchanged
        
        # Verify persistence
        retrieved = test_db_session.query(Budget).filter(
            Budget.id == budget.id
        ).first()
        assert retrieved.amount_cents == 35000
        assert retrieved.name == "Partial Update Test"


class TestBudgetServiceDeleteIntegration:
    """Integration tests for budget deletion."""
    
    def test_delete_budget_integration(self, test_db_session, test_user):
        """Test budget deletion with real database."""
        # Arrange - Create budget to delete
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            name="Budget to Delete",
            amount_cents=20000,
            period="monthly",
            start_date=date.today(),
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        budget_id = budget.id
        
        # Act - Delete the budget
        result = BudgetService.delete_budget(test_db_session, budget)
        
        # Assert
        assert result is True
        
        # Verify budget was actually deleted from database
        retrieved = test_db_session.query(Budget).filter(
            Budget.id == budget_id
        ).first()
        assert retrieved is None


class TestBudgetServiceCalculateBudgetUsageIntegration:
    """Integration tests for budget usage calculation."""
    
    def test_calculate_budget_usage_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget usage calculation with real transactions."""
        # Arrange - Create budget
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            amount_cents=50000,  # $500 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Create transactions that fall within budget period and category
        transactions_data = [
            (15000, date(2025, 1, 5)),   # $150
            (12000, date(2025, 1, 15)),  # $120
            (8000, date(2025, 1, 25)),   # $80
        ]
        
        for amount_cents, trans_date in transactions_data:
            transaction = Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=test_category.id,
                amount_cents=amount_cents,
                currency="USD",
                description="Test transaction",
                transaction_date=trans_date,
                status="posted"
            )
            test_db_session.add(transaction)
        
        test_db_session.commit()
        
        # Act
        result = BudgetService.calculate_budget_usage(test_db_session, budget)
        
        # Assert
        assert isinstance(result, BudgetUsage)
        assert result.budget_id == budget.id
        assert result.spent_cents == 35000  # $350 total (150 + 120 + 80)
        assert result.remaining_cents == 15000  # $150 remaining (500 - 350)
        assert result.percentage_used == 0.7  # 35000 / 50000
        assert result.is_over_budget is False

    def test_calculate_budget_usage_over_budget_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget usage calculation when over budget."""
        # Arrange - Create small budget
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            amount_cents=30000,  # $300 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Create transactions that exceed budget
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=40000,  # $400 (exceeds $300 budget)
            currency="USD",
            description="Over budget transaction",
            transaction_date=date(2025, 1, 15),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act
        result = BudgetService.calculate_budget_usage(test_db_session, budget)
        
        # Assert
        assert result.spent_cents == 40000
        assert result.remaining_cents == -10000  # Over budget by $100
        assert abs(result.percentage_used - 1.333) < 0.01  # ~133%
        assert result.is_over_budget is True

    def test_calculate_budget_usage_no_transactions_integration(
        self, test_db_session, test_user, test_category
    ):
        """Test budget usage calculation with no transactions."""
        # Arrange - Create budget with no transactions
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            amount_cents=40000,  # $400 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Act (no transactions created)
        result = BudgetService.calculate_budget_usage(test_db_session, budget)
        
        # Assert
        assert result.spent_cents == 0
        assert result.remaining_cents == 40000
        assert result.percentage_used == 0.0
        assert result.is_over_budget is False


class TestBudgetServiceGetBudgetAlertsIntegration:
    """Integration tests for budget alerts."""
    
    def test_get_budget_alerts_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget alerts generation with real data."""
        # Arrange - Create budget with alert threshold
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            name="Alert Test Budget",
            amount_cents=50000,  # $500
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            alert_threshold=0.8,  # 80% threshold
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Create transaction that pushes spending over threshold
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=42000,  # $420 (84% of $500 budget)
            currency="USD",
            description="High spending transaction",
            transaction_date=date(2025, 1, 15),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act
        result = BudgetService.get_budget_alerts(test_db_session, test_user.id)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        
        alert = result[0]
        assert isinstance(alert, BudgetAlert)
        assert alert.budget_id == budget.id
        assert alert.budget_name == "Alert Test Budget"
        assert alert.category_name == test_category.name
        assert alert.alert_type == "warning"  # Over threshold but not over budget
        assert alert.percentage_used == 0.84
        assert "84%" in alert.message
        assert alert.amount_over is None  # Not over budget

    def test_get_budget_alerts_no_alerts_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test budget alerts when no alerts should be generated."""
        # Arrange - Create budget
        budget = Budget(
            id=uuid4(),
            user_id=test_user.id,
            category_id=test_category.id,
            name="Low Usage Budget",
            amount_cents=50000,  # $500
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            alert_threshold=0.8,  # 80% threshold
            is_active=True
        )
        test_db_session.add(budget)
        test_db_session.commit()
        
        # Create transaction well below threshold
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=test_category.id,
            amount_cents=25000,  # $250 (50% of $500 budget - below 80% threshold)
            currency="USD",
            description="Low spending transaction",
            transaction_date=date(2025, 1, 15),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act
        result = BudgetService.get_budget_alerts(test_db_session, test_user.id)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 0  # No alerts should be generated


# Test markers
pytestmark = pytest.mark.integration