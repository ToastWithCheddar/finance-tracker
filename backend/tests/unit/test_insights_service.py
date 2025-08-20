import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.insights_service import InsightsService
from app.models.insight import Insight
from app.models.transaction import Transaction
from app.models.goal import Goal, GoalStatus
from app.models.category import Category
from app.schemas.insight import InsightType, InsightPriority


class TestInsightsService:
    """Test suite for InsightsService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.insights_service = InsightsService(self.mock_db)
        self.user_id = uuid4()
        self.category_id = uuid4()
        self.goal_id = uuid4()
        self.account_id = uuid4()
    
    def test_generate_insights_for_user_success(self):
        """Test successful insight generation for user."""
        # Mock the private methods
        with patch.object(self.insights_service, '_generate_spending_spike_insights') as mock_spending, \
             patch.object(self.insights_service, '_generate_recurring_expense_insights') as mock_recurring, \
             patch.object(self.insights_service, '_generate_goal_progress_insights') as mock_goal:
            
            # Mock return values
            spending_insight = Mock(spec=Insight)
            recurring_insight = Mock(spec=Insight)
            goal_insight = Mock(spec=Insight)
            
            mock_spending.return_value = [spending_insight]
            mock_recurring.return_value = [recurring_insight]
            mock_goal.return_value = [goal_insight]
            
            # Call the method
            result = self.insights_service.generate_insights_for_user(self.mock_db, self.user_id)
            
            # Assertions
            assert len(result) == 3
            assert spending_insight in result
            assert recurring_insight in result
            assert goal_insight in result
            
            # Verify all methods were called
            mock_spending.assert_called_once_with(self.mock_db, self.user_id)
            mock_recurring.assert_called_once_with(self.mock_db, self.user_id)
            mock_goal.assert_called_once_with(self.mock_db, self.user_id)
    
    def test_generate_spending_spike_insights_with_spike(self):
        """Test spending spike detection with valid spike."""
        # Mock date calculations
        today = date(2024, 1, 31)
        thirty_days_ago = date(2024, 1, 1)
        sixty_days_ago = date(2023, 12, 2)
        
        with patch('app.services.insights_service.date') as mock_date:
            mock_date.today.return_value = today
            
            # Mock current spending query result
            current_result = Mock()
            current_result.category_id = self.category_id
            current_result.total_cents = 30000  # $300
            
            # Mock previous spending query result
            previous_result = Mock()
            previous_result.category_id = self.category_id
            previous_result.total_cents = 15000  # $150
            
            # Mock database queries
            self.mock_db.query.return_value.filter.return_value.group_by.return_value.all.side_effect = [
                [current_result],  # Current spending
                [previous_result]  # Previous spending
            ]
            
            # Mock category query
            mock_category = Mock(spec=Category)
            mock_category.name = "Dining Out"
            self.mock_db.query.return_value.filter.return_value.first.return_value = mock_category
            
            # Mock has_recent_insight to return False (no recent insights)
            with patch.object(self.insights_service, '_has_recent_insight', return_value=False):
                # Mock _create_spending_spike_insight
                mock_insight = Mock(spec=Insight)
                with patch.object(self.insights_service, '_create_spending_spike_insight', return_value=mock_insight):
                    
                    # Call the method
                    result = self.insights_service._generate_spending_spike_insights(self.mock_db, self.user_id)
                    
                    # Assertions
                    assert len(result) == 1
                    assert result[0] == mock_insight
    
    def test_generate_spending_spike_insights_no_spike(self):
        """Test spending spike detection with no significant spike."""
        # Mock date calculations
        today = date(2024, 1, 31)
        
        with patch('app.services.insights_service.date') as mock_date:
            mock_date.today.return_value = today
            
            # Mock current spending query result (small increase)
            current_result = Mock()
            current_result.category_id = self.category_id
            current_result.total_cents = 10500  # $105
            
            # Mock previous spending query result
            previous_result = Mock()
            previous_result.category_id = self.category_id
            previous_result.total_cents = 10000  # $100
            
            # Mock database queries
            self.mock_db.query.return_value.filter.return_value.group_by.return_value.all.side_effect = [
                [current_result],  # Current spending
                [previous_result]  # Previous spending
            ]
            
            # Call the method
            result = self.insights_service._generate_spending_spike_insights(self.mock_db, self.user_id)
            
            # Assertions - no insights should be created for small increase
            assert len(result) == 0
    
    def test_generate_recurring_expense_insights_high_confidence(self):
        """Test recurring expense detection with high confidence suggestion."""
        # Mock recurring detection service
        high_confidence_suggestion = {
            'merchant': 'Netflix',
            'normalized_merchant': 'netflix',
            'amount_dollars': 15.99,
            'amount_cents': 1599,
            'frequency': 'monthly',
            'confidence_score': 0.95,
            'transaction_count': 4,
            'category_id': str(self.category_id),
            'account_id': str(self.account_id)
        }
        
        self.insights_service.recurring_service.get_suggestions_for_user.return_value = [
            high_confidence_suggestion
        ]
        
        # Mock has_recent_insight to return False
        with patch.object(self.insights_service, '_has_recent_insight', return_value=False):
            # Mock _create_recurring_expense_insight
            mock_insight = Mock(spec=Insight)
            with patch.object(self.insights_service, '_create_recurring_expense_insight', return_value=mock_insight):
                
                # Call the method
                result = self.insights_service._generate_recurring_expense_insights(self.mock_db, self.user_id)
                
                # Assertions
                assert len(result) == 1
                assert result[0] == mock_insight
    
    def test_generate_recurring_expense_insights_low_confidence(self):
        """Test recurring expense detection with low confidence suggestion."""
        # Mock recurring detection service with low confidence
        low_confidence_suggestion = {
            'merchant': 'Some Merchant',
            'normalized_merchant': 'some merchant',
            'amount_dollars': 25.00,
            'confidence_score': 0.60,  # Below threshold
            'frequency': 'monthly'
        }
        
        self.insights_service.recurring_service.get_suggestions_for_user.return_value = [
            low_confidence_suggestion
        ]
        
        # Call the method
        result = self.insights_service._generate_recurring_expense_insights(self.mock_db, self.user_id)
        
        # Assertions - no insights should be created for low confidence
        assert len(result) == 0
    
    def test_generate_goal_progress_insights_behind_schedule(self):
        """Test goal progress detection for goal behind schedule."""
        # Mock goal that's behind schedule
        mock_goal = Mock(spec=Goal)
        mock_goal.id = self.goal_id
        mock_goal.user_id = self.user_id
        mock_goal.name = "Emergency Fund"
        mock_goal.status = 'active'
        mock_goal.start_date = date(2024, 1, 1)
        mock_goal.target_date = date(2024, 12, 31)  # 365 days total
        mock_goal.progress_percentage = 20  # 20% complete
        mock_goal.remaining = 8000  # $80 remaining
        mock_goal.days_remaining = 300
        
        # Mock database query
        self.mock_db.query.return_value.filter.return_value.all.return_value = [mock_goal]
        
        # Mock current date to be 6 months in (should be ~50% complete, but only 20%)
        today = date(2024, 7, 1)  # 6 months in
        with patch('app.services.insights_service.date') as mock_date:
            mock_date.today.return_value = today
            
            # Mock has_recent_insight to return False
            with patch.object(self.insights_service, '_has_recent_insight', return_value=False):
                # Mock _create_goal_progress_insight
                mock_insight = Mock(spec=Insight)
                with patch.object(self.insights_service, '_create_goal_progress_insight', return_value=mock_insight):
                    
                    # Call the method
                    result = self.insights_service._generate_goal_progress_insights(self.mock_db, self.user_id)
                    
                    # Assertions
                    assert len(result) == 1
                    assert result[0] == mock_insight
    
    def test_generate_goal_progress_insights_on_track(self):
        """Test goal progress detection for goal on track."""
        # Mock goal that's on track
        mock_goal = Mock(spec=Goal)
        mock_goal.id = self.goal_id
        mock_goal.user_id = self.user_id
        mock_goal.name = "Vacation Fund"
        mock_goal.status = 'active'
        mock_goal.start_date = date(2024, 1, 1)
        mock_goal.target_date = date(2024, 12, 31)
        mock_goal.progress_percentage = 50  # 50% complete
        mock_goal.remaining = 5000
        mock_goal.days_remaining = 180
        
        # Mock database query
        self.mock_db.query.return_value.filter.return_value.all.return_value = [mock_goal]
        
        # Mock current date to be 6 months in (should be ~50% complete, and is 50%)
        today = date(2024, 7, 1)
        with patch('app.services.insights_service.date') as mock_date:
            mock_date.today.return_value = today
            
            # Call the method
            result = self.insights_service._generate_goal_progress_insights(self.mock_db, self.user_id)
            
            # Assertions - no insights should be created for on-track goal
            assert len(result) == 0
    
    def test_has_recent_insight_exists(self):
        """Test duplicate prevention when recent insight exists."""
        # Mock query result with existing insight
        existing_insight = Mock(spec=Insight)
        self.mock_db.query.return_value.filter.return_value.first.return_value = existing_insight
        
        # Call the method
        result = self.insights_service._has_recent_insight(
            self.mock_db, self.user_id, InsightType.SPENDING_SPIKE, category_id=self.category_id
        )
        
        # Assertions
        assert result is True
    
    def test_has_recent_insight_not_exists(self):
        """Test duplicate prevention when no recent insight exists."""
        # Mock query result with no existing insight
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Call the method
        result = self.insights_service._has_recent_insight(
            self.mock_db, self.user_id, InsightType.SPENDING_SPIKE, category_id=self.category_id
        )
        
        # Assertions
        assert result is False
    
    def test_create_spending_spike_insight(self):
        """Test spending spike insight creation."""
        category_name = "Dining Out"
        current_amount = 25000  # $250
        previous_amount = 15000  # $150
        increase_percent = 0.67  # 67%
        
        # Mock database operations
        mock_insight = Mock(spec=Insight)
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        
        # Create a real Insight object for testing
        with patch('app.services.insights_service.Insight') as MockInsight:
            MockInsight.return_value = mock_insight
            
            # Call the method
            result = self.insights_service._create_spending_spike_insight(
                self.mock_db, self.user_id, self.category_id, category_name,
                current_amount, previous_amount, increase_percent
            )
            
            # Assertions
            assert result == mock_insight
            self.mock_db.add.assert_called_once_with(mock_insight)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(mock_insight)
            
            # Verify Insight was created with correct parameters
            MockInsight.assert_called_once()
            call_kwargs = MockInsight.call_args[1]
            assert call_kwargs['user_id'] == self.user_id
            assert call_kwargs['type'] == InsightType.SPENDING_SPIKE.value
            assert category_name in call_kwargs['title']
            assert "67%" in call_kwargs['description']
            assert "$250.00" in call_kwargs['description']
    
    def test_create_recurring_expense_insight(self):
        """Test recurring expense insight creation."""
        suggestion = {
            'merchant': 'Netflix',
            'normalized_merchant': 'netflix',
            'amount_dollars': 15.99,
            'amount_cents': 1599,
            'frequency': 'monthly',
            'confidence_score': 0.95,
            'transaction_count': 4,
            'category_id': str(self.category_id),
            'account_id': str(self.account_id)
        }
        
        # Mock database operations
        mock_insight = Mock(spec=Insight)
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        
        # Create a real Insight object for testing
        with patch('app.services.insights_service.Insight') as MockInsight:
            MockInsight.return_value = mock_insight
            
            # Call the method
            result = self.insights_service._create_recurring_expense_insight(
                self.mock_db, self.user_id, suggestion
            )
            
            # Assertions
            assert result == mock_insight
            self.mock_db.add.assert_called_once_with(mock_insight)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(mock_insight)
            
            # Verify Insight was created with correct parameters
            MockInsight.assert_called_once()
            call_kwargs = MockInsight.call_args[1]
            assert call_kwargs['user_id'] == self.user_id
            assert call_kwargs['type'] == InsightType.RECURRING_EXPENSE.value
            assert "Netflix" in call_kwargs['description']
            assert "monthly" in call_kwargs['description']
    
    def test_create_goal_progress_insight(self):
        """Test goal progress insight creation."""
        # Mock goal
        mock_goal = Mock(spec=Goal)
        mock_goal.id = self.goal_id
        mock_goal.name = "Emergency Fund"
        mock_goal.remaining = 8000  # $80
        mock_goal.days_remaining = 300
        mock_goal.target_date = date(2024, 12, 31)
        
        expected_progress = 0.50  # 50%
        actual_progress = 0.20   # 20%
        progress_deviation = 0.30 # 30%
        
        # Mock database operations
        mock_insight = Mock(spec=Insight)
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        
        # Create a real Insight object for testing
        with patch('app.services.insights_service.Insight') as MockInsight:
            MockInsight.return_value = mock_insight
            
            # Call the method
            result = self.insights_service._create_goal_progress_insight(
                self.mock_db, self.user_id, mock_goal,
                expected_progress, actual_progress, progress_deviation
            )
            
            # Assertions
            assert result == mock_insight
            self.mock_db.add.assert_called_once_with(mock_insight)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(mock_insight)
            
            # Verify Insight was created with correct parameters
            MockInsight.assert_called_once()
            call_kwargs = MockInsight.call_args[1]
            assert call_kwargs['user_id'] == self.user_id
            assert call_kwargs['type'] == InsightType.GOAL_PROGRESS.value
            assert call_kwargs['priority'] == InsightPriority.HIGH.value
            assert "Emergency Fund" in call_kwargs['title']
            assert "30%" in call_kwargs['description']
    
    def test_generate_insights_handles_exceptions(self):
        """Test that insight generation handles exceptions gracefully."""
        # Mock one method to raise an exception
        with patch.object(self.insights_service, '_generate_spending_spike_insights', 
                         side_effect=Exception("Database error")):
            
            # Call should raise the exception
            with pytest.raises(Exception, match="Database error"):
                self.insights_service.generate_insights_for_user(self.mock_db, self.user_id)
    
    def test_spending_spike_insights_handles_none_category(self):
        """Test spending spike detection handles transactions with None category."""
        today = date(2024, 1, 31)
        
        with patch('app.services.insights_service.date') as mock_date:
            mock_date.today.return_value = today
            
            # Mock query results with None category
            current_result = Mock()
            current_result.category_id = None
            current_result.total_cents = 30000
            
            previous_result = Mock()
            previous_result.category_id = None
            previous_result.total_cents = 15000
            
            self.mock_db.query.return_value.filter.return_value.group_by.return_value.all.side_effect = [
                [current_result],
                [previous_result]
            ]
            
            # Call the method
            result = self.insights_service._generate_spending_spike_insights(self.mock_db, self.user_id)
            
            # Should return empty list for None categories
            assert len(result) == 0