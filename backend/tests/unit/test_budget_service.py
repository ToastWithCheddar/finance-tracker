"""
Unit tests for BudgetService.

These tests focus on testing the business logic of BudgetService 
in isolation by mocking all external dependencies including the database.
"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.budget_service import BudgetService
from app.schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetUsage, 
    BudgetAlert, BudgetSummary, BudgetProgress, BudgetFilter,
    BudgetPeriod
)
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction


class TestBudgetServiceCreateBudget:
    """Test the create_budget method."""
    
    def test_create_budget_success(self, mocker):
        """Test successful budget creation."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        budget_data = BudgetCreate(
            name="Groceries Budget",
            category_id=uuid4(),
            amount_cents=50000,  # $500.00
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.8,
            is_active=True
        )
        
        mock_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            **budget_data.model_dump()
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mocker.patch('app.services.budget_service.Budget', return_value=mock_budget)
        
        # Act
        result = BudgetService.create_budget(mock_db, budget_data, user_id)
        
        # Assert
        assert result == mock_budget
        assert result.user_id == user_id
        assert result.name == "Groceries Budget"
        assert result.amount_cents == 50000
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_budget_without_category(self, mocker):
        """Test budget creation without category (overall budget)."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        budget_data = BudgetCreate(
            name="Overall Monthly Budget",
            category_id=None,  # No specific category
            amount_cents=200000,  # $2000.00
            period="monthly",
            start_date=date.today(),
            alert_threshold=0.9,
            is_active=True
        )
        
        mock_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            **budget_data.model_dump()
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mocker.patch('app.services.budget_service.Budget', return_value=mock_budget)
        
        # Act
        result = BudgetService.create_budget(mock_db, budget_data, user_id)
        
        # Assert
        assert result == mock_budget
        assert result.category_id is None
        assert result.name == "Overall Monthly Budget"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestBudgetServiceGetBudget:
    """Test the get_budget method."""
    
    def test_get_budget_success(self, mocker):
        """Test successful budget retrieval with eager loading."""
        # Arrange
        mock_db = MagicMock()
        budget_id = uuid4()
        user_id = uuid4()
        
        mock_category = Category(id=uuid4(), name="Test Category")
        mock_budget = Budget(
            id=budget_id,
            user_id=user_id,
            name="Test Budget",
            amount_cents=30000,
            category=mock_category
        )
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_budget
        
        mocker.patch('app.services.budget_service.joinedload')
        
        # Act
        result = BudgetService.get_budget(mock_db, budget_id, user_id)
        
        # Assert
        assert result == mock_budget
        assert result.category == mock_category
        mock_db.query.assert_called_once_with(Budget)
        mock_query.options.assert_called_once()
        mock_query.filter.assert_called_once()

    def test_get_budget_not_found(self, mocker):
        """Test budget not found scenario."""
        # Arrange
        mock_db = MagicMock()
        budget_id = uuid4()
        user_id = uuid4()
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        mocker.patch('app.services.budget_service.joinedload')
        
        # Act
        result = BudgetService.get_budget(mock_db, budget_id, user_id)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once_with(Budget)


class TestBudgetServiceGetBudgets:
    """Test the get_budgets method."""
    
    def test_get_budgets_success_with_filters(self, mocker):
        """Test successful budgets retrieval with filters."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        category_id = uuid4()
        
        filters = BudgetFilter(
            category_id=str(category_id),
            period=BudgetPeriod.monthly,
            is_active=True
        )
        
        mock_budgets = [
            Budget(id=uuid4(), user_id=user_id, name="Budget 1", amount_cents=30000),
            Budget(id=uuid4(), user_id=user_id, name="Budget 2", amount_cents=40000),
        ]
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_budgets
        
        mocker.patch('app.services.budget_service.joinedload')
        
        # Act
        result = BudgetService.get_budgets(mock_db, user_id, filters, skip=0, limit=100)
        
        # Assert
        assert result == mock_budgets
        mock_db.query.assert_called_once_with(Budget)
        mock_query.options.assert_called_once()
        
        # Verify filters were applied (multiple filter calls for different criteria)
        assert mock_query.filter.call_count >= 4  # user_id + category_id + period + is_active

    def test_get_budgets_no_filters(self, mocker):
        """Test budgets retrieval without filters."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        mock_budgets = [Budget(id=uuid4(), user_id=user_id, name="Budget 1")]
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_budgets
        
        mocker.patch('app.services.budget_service.joinedload')
        
        # Act
        result = BudgetService.get_budgets(mock_db, user_id, filters=None, skip=0, limit=100)
        
        # Assert
        assert result == mock_budgets
        mock_db.query.assert_called_once_with(Budget)
        # Should only filter by user_id when no filters provided
        mock_query.filter.assert_called_once()

    def test_get_budgets_with_pagination(self, mocker):
        """Test budgets retrieval with pagination."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        mock_budgets = [Budget(id=uuid4(), user_id=user_id, name="Budget 1")]
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_budgets
        
        mocker.patch('app.services.budget_service.joinedload')
        
        # Act
        result = BudgetService.get_budgets(mock_db, user_id, filters=None, skip=10, limit=25)
        
        # Assert
        assert result == mock_budgets
        mock_query.offset.assert_called_once_with(10)
        mock_query.limit.assert_called_once_with(25)


class TestBudgetServiceUpdateBudget:
    """Test the update_budget method."""
    
    def test_update_budget_success(self, mocker):
        """Test successful budget update."""
        # Arrange
        mock_db = MagicMock()
        
        original_budget = Budget(
            id=uuid4(),
            name="Original Budget",
            amount_cents=30000,
            alert_threshold=0.8,
            is_active=True
        )
        
        update_data = BudgetUpdate(
            name="Updated Budget",
            amount_cents=40000,
            alert_threshold=0.9
        )
        
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock datetime for updated_at
        mock_datetime = mocker.patch('app.services.budget_service.datetime')
        mock_datetime.utcnow.return_value = datetime(2025, 1, 15, 12, 0, 0)
        
        # Act
        result = BudgetService.update_budget(mock_db, original_budget, update_data)
        
        # Assert
        assert result == original_budget
        assert result.name == "Updated Budget"
        assert result.amount_cents == 40000
        assert result.alert_threshold == 0.9
        assert result.is_active is True  # Should remain unchanged
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(original_budget)

    def test_update_budget_partial_update(self, mocker):
        """Test partial budget update (only some fields)."""
        # Arrange
        mock_db = MagicMock()
        
        original_budget = Budget(
            id=uuid4(),
            name="Original Budget",
            amount_cents=30000,
            alert_threshold=0.8,
            is_active=True
        )
        
        update_data = BudgetUpdate(
            amount_cents=35000  # Only updating amount
        )
        
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mock_datetime = mocker.patch('app.services.budget_service.datetime')
        mock_datetime.utcnow.return_value = datetime(2025, 1, 15, 12, 0, 0)
        
        # Act
        result = BudgetService.update_budget(mock_db, original_budget, update_data)
        
        # Assert
        assert result == original_budget
        assert result.amount_cents == 35000  # Updated
        assert result.name == "Original Budget"  # Unchanged
        assert result.alert_threshold == 0.8  # Unchanged
        assert result.is_active is True  # Unchanged
        mock_db.commit.assert_called_once()


class TestBudgetServiceDeleteBudget:
    """Test the delete_budget method."""
    
    def test_delete_budget_success(self, mocker):
        """Test successful budget deletion."""
        # Arrange
        mock_db = MagicMock()
        
        budget = Budget(
            id=uuid4(),
            name="Budget to delete",
            amount_cents=30000
        )
        
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None
        
        # Act
        result = BudgetService.delete_budget(mock_db, budget)
        
        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(budget)
        mock_db.commit.assert_called_once()


class TestBudgetServiceCalculateBudgetUsage:
    """Test the calculate_budget_usage method."""
    
    def test_calculate_budget_usage_success(self, mocker):
        """Test budget usage calculation."""
        # Arrange
        mock_db = MagicMock()
        
        budget = Budget(
            id=uuid4(),
            amount_cents=50000,  # $500 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        
        # Mock query to return spent amount
        mock_query = mock_db.query.return_value
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 30000  # $300 spent
        
        # Act
        result = BudgetService.calculate_budget_usage(mock_db, budget)
        
        # Assert
        assert isinstance(result, BudgetUsage)
        assert result.budget_id == budget.id
        assert result.spent_cents == 30000
        assert result.remaining_cents == 20000  # 50000 - 30000
        assert result.percentage_used == 0.6  # 30000 / 50000
        assert result.is_over_budget is False
        
        # Verify database query was made
        mock_db.query.assert_called_once()

    def test_calculate_budget_usage_over_budget(self, mocker):
        """Test budget usage calculation when over budget."""
        # Arrange
        mock_db = MagicMock()
        
        budget = Budget(
            id=uuid4(),
            amount_cents=50000,  # $500 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        
        # Mock query to return spent amount over budget
        mock_query = mock_db.query.return_value
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 60000  # $600 spent (over $500 budget)
        
        # Act
        result = BudgetService.calculate_budget_usage(mock_db, budget)
        
        # Assert
        assert isinstance(result, BudgetUsage)
        assert result.budget_id == budget.id
        assert result.spent_cents == 60000
        assert result.remaining_cents == -10000  # 50000 - 60000 (negative)
        assert result.percentage_used == 1.2  # 60000 / 50000
        assert result.is_over_budget is True

    def test_calculate_budget_usage_no_spending(self, mocker):
        """Test budget usage calculation with no spending."""
        # Arrange
        mock_db = MagicMock()
        
        budget = Budget(
            id=uuid4(),
            amount_cents=50000,  # $500 budget
            period="monthly",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31)
        )
        
        # Mock query to return no spending
        mock_query = mock_db.query.return_value
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None  # No spending
        
        # Act
        result = BudgetService.calculate_budget_usage(mock_db, budget)
        
        # Assert
        assert isinstance(result, BudgetUsage)
        assert result.budget_id == budget.id
        assert result.spent_cents == 0
        assert result.remaining_cents == 50000
        assert result.percentage_used == 0.0
        assert result.is_over_budget is False


class TestBudgetServiceGetBudgetAlerts:
    """Test the get_budget_alerts method."""
    
    def test_get_budget_alerts_success(self, mocker):
        """Test budget alerts generation."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        # Mock budget with category
        mock_category = Category(id=uuid4(), name="Groceries")
        mock_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            name="Groceries Budget",
            amount_cents=50000,  # $500
            alert_threshold=0.8,  # 80% threshold
            category=mock_category,
            is_active=True
        )
        
        mock_budgets_query = mock_db.query.return_value
        mock_budgets_query.options.return_value = mock_budgets_query
        mock_budgets_query.filter.return_value = mock_budgets_query
        mock_budgets_query.all.return_value = [mock_budget]
        
        # Mock usage calculation to return over-threshold spending
        mock_usage = BudgetUsage(
            budget_id=mock_budget.id,
            spent_cents=42000,  # $420 (84% of $500)
            remaining_cents=8000,
            percentage_used=0.84,
            is_over_budget=False
        )
        
        mocker.patch('app.services.budget_service.joinedload')
        mocker.patch.object(BudgetService, 'calculate_budget_usage', return_value=mock_usage)
        
        # Act
        result = BudgetService.get_budget_alerts(mock_db, user_id)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        
        alert = result[0]
        assert isinstance(alert, BudgetAlert)
        assert alert.budget_id == mock_budget.id
        assert alert.budget_name == "Groceries Budget"
        assert alert.category_name == "Groceries"
        assert alert.alert_type == "warning"  # Over threshold but not over budget
        assert alert.percentage_used == 0.84
        assert "84%" in alert.message

    def test_get_budget_alerts_over_budget(self, mocker):
        """Test budget alerts for over-budget scenario."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        mock_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            name="Entertainment Budget",
            amount_cents=30000,  # $300
            alert_threshold=0.8,
            category=None,  # No category
            is_active=True
        )
        
        mock_budgets_query = mock_db.query.return_value
        mock_budgets_query.options.return_value = mock_budgets_query
        mock_budgets_query.filter.return_value = mock_budgets_query
        mock_budgets_query.all.return_value = [mock_budget]
        
        # Mock usage calculation to return over-budget spending
        mock_usage = BudgetUsage(
            budget_id=mock_budget.id,
            spent_cents=35000,  # $350 (over $300 budget)
            remaining_cents=-5000,
            percentage_used=1.17,
            is_over_budget=True
        )
        
        mocker.patch('app.services.budget_service.joinedload')
        mocker.patch.object(BudgetService, 'calculate_budget_usage', return_value=mock_usage)
        
        # Act
        result = BudgetService.get_budget_alerts(mock_db, user_id)
        
        # Assert
        assert len(result) == 1
        
        alert = result[0]
        assert alert.alert_type == "exceeded"  # Over budget
        assert alert.amount_over == 50.0  # $50 over budget
        assert alert.percentage_used == 1.17

    def test_get_budget_alerts_no_alerts(self, mocker):
        """Test budget alerts when no alerts are needed."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        mock_budget = Budget(
            id=uuid4(),
            user_id=user_id,
            name="Low Usage Budget",
            amount_cents=50000,  # $500
            alert_threshold=0.8,
            category=None,
            is_active=True
        )
        
        mock_budgets_query = mock_db.query.return_value
        mock_budgets_query.options.return_value = mock_budgets_query
        mock_budgets_query.filter.return_value = mock_budgets_query
        mock_budgets_query.all.return_value = [mock_budget]
        
        # Mock usage calculation to return low spending (below threshold)
        mock_usage = BudgetUsage(
            budget_id=mock_budget.id,
            spent_cents=25000,  # $250 (50% of $500 - below 80% threshold)
            remaining_cents=25000,
            percentage_used=0.5,
            is_over_budget=False
        )
        
        mocker.patch('app.services.budget_service.joinedload')
        mocker.patch.object(BudgetService, 'calculate_budget_usage', return_value=mock_usage)
        
        # Act
        result = BudgetService.get_budget_alerts(mock_db, user_id)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 0  # No alerts should be generated


# Test markers
pytestmark = pytest.mark.unit