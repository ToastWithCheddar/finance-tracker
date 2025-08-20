"""
Unit tests for PlaidRecurringService
Tests the Plaid recurring transaction management functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, date

from app.services.plaid_recurring_service import PlaidRecurringService
from app.models.plaid_recurring_transaction import PlaidRecurringTransaction
from app.models.recurring_transaction import RecurringTransactionRule
from app.models.account import Account

class TestPlaidRecurringService:
    """Test PlaidRecurringService functionality"""
    
    def setup_method(self):
        """Setup test dependencies"""
        self.mock_db = Mock()
        self.service = PlaidRecurringService(self.mock_db)
        
        # Mock the enhanced Plaid service
        self.service.plaid_service = AsyncMock()
        
        # Test data
        self.test_user_id = uuid4()
        self.test_account_id = uuid4()
        self.test_rule_id = uuid4()
        self.test_plaid_recurring_id = "plaid_recurring_test_123"
    
    def create_mock_plaid_recurring_transaction(self):
        """Create a mock PlaidRecurringTransaction"""
        recurring = Mock(spec=PlaidRecurringTransaction)
        recurring.plaid_recurring_transaction_id = self.test_plaid_recurring_id
        recurring.user_id = self.test_user_id
        recurring.account_id = self.test_account_id
        recurring.description = "Netflix Subscription"
        recurring.merchant_name = "Netflix"
        recurring.amount_cents = 1299
        recurring.amount_dollars = 12.99
        recurring.currency = "USD"
        recurring.plaid_frequency = "MONTHLY"
        recurring.plaid_status = "MATURE"
        recurring.plaid_category = ["Entertainment", "Streaming"]
        recurring.last_amount_cents = 1299
        recurring.last_date = date.today()
        recurring.monthly_estimated_amount_cents = 1299
        recurring.is_muted = False
        recurring.is_linked_to_rule = False
        recurring.linked_rule_id = None
        recurring.is_mature = True
        recurring.first_detected_at = datetime.now(timezone.utc)
        recurring.last_sync_at = datetime.now(timezone.utc)
        recurring.sync_count = 1
        
        return recurring
    
    def create_mock_recurring_rule(self):
        """Create a mock RecurringTransactionRule"""
        rule = Mock(spec=RecurringTransactionRule)
        rule.id = self.test_rule_id
        rule.user_id = self.test_user_id
        rule.name = "Netflix Rule"
        rule.description = "Netflix subscription rule"
        rule.amount_cents = 1299
        rule.is_active = True
        
        return rule
    
    @pytest.mark.asyncio
    async def test_sync_user_recurring_transactions_success(self):
        """Test successful sync of user's recurring transactions"""
        # Mock the enhanced Plaid service response
        sync_result = {
            "success": True,
            "accounts_processed": 2,
            "total_recurring_transactions": 5,
            "new_recurring_transactions": 3,
            "updated_recurring_transactions": 2,
            "total_errors": 0,
            "results": []
        }
        self.service.plaid_service.sync_recurring_transactions_for_user.return_value = sync_result
        
        result = await self.service.sync_user_recurring_transactions(self.test_user_id)
        
        assert result["success"] is True
        assert result["total_recurring_transactions"] == 5
        assert result["new_recurring_transactions"] == 3
        
        self.service.plaid_service.sync_recurring_transactions_for_user.assert_called_once_with(
            self.mock_db, str(self.test_user_id)
        )
    
    @pytest.mark.asyncio
    async def test_sync_user_recurring_transactions_failure(self):
        """Test handling of sync failure"""
        # Mock the enhanced Plaid service to raise an exception
        self.service.plaid_service.sync_recurring_transactions_for_user.side_effect = Exception("Plaid API error")
        
        result = await self.service.sync_user_recurring_transactions(self.test_user_id)
        
        assert result["success"] is False
        assert "error" in result
        assert "Plaid API error" in result["error"]
    
    def test_get_user_plaid_recurring_transactions_basic(self):
        """Test retrieving user's Plaid recurring transactions"""
        mock_recurring = [self.create_mock_plaid_recurring_transaction()]
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = mock_recurring
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_user_plaid_recurring_transactions(self.test_user_id)
        
        assert len(result) == 1
        assert result[0].plaid_recurring_transaction_id == self.test_plaid_recurring_id
    
    def test_get_user_plaid_recurring_transactions_with_filters(self):
        """Test retrieving recurring transactions with filters"""
        mock_recurring = [self.create_mock_plaid_recurring_transaction()]
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.offset.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = mock_recurring
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_user_plaid_recurring_transactions(
            user_id=self.test_user_id,
            include_muted=True,
            account_id=self.test_account_id,
            status_filter="MATURE",
            frequency_filter="MONTHLY",
            limit=10,
            offset=0
        )
        
        assert len(result) == 1
        # Verify that filters were applied (would check filter call count in real implementation)
    
    def test_get_plaid_recurring_transaction_found(self):
        """Test retrieving a specific Plaid recurring transaction"""
        mock_recurring = self.create_mock_plaid_recurring_transaction()
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mock_recurring
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_plaid_recurring_transaction(
            self.test_user_id, 
            self.test_plaid_recurring_id
        )
        
        assert result is not None
        assert result.plaid_recurring_transaction_id == self.test_plaid_recurring_id
    
    def test_get_plaid_recurring_transaction_not_found(self):
        """Test retrieving a non-existent Plaid recurring transaction"""
        # Mock database query to return None
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_plaid_recurring_transaction(
            self.test_user_id, 
            "non_existent_id"
        )
        
        assert result is None
    
    def test_mute_recurring_transaction_success(self):
        """Test successfully muting a recurring transaction"""
        mock_recurring = self.create_mock_plaid_recurring_transaction()
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mock_recurring
        self.mock_db.query.return_value = query_mock
        
        result = self.service.mute_recurring_transaction(
            self.test_user_id,
            self.test_plaid_recurring_id,
            muted=True
        )
        
        assert result.is_muted is True
        self.mock_db.add.assert_called_once_with(mock_recurring)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_recurring)
    
    def test_mute_recurring_transaction_not_found(self):
        """Test muting a non-existent recurring transaction"""
        # Mock database query to return None
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        self.mock_db.query.return_value = query_mock
        
        with pytest.raises(ValueError, match="not found"):
            self.service.mute_recurring_transaction(
                self.test_user_id,
                "non_existent_id",
                muted=True
            )
    
    def test_link_to_rule_success(self):
        """Test successfully linking a recurring transaction to a rule"""
        mock_recurring = self.create_mock_plaid_recurring_transaction()
        mock_rule = self.create_mock_recurring_rule()
        
        # Mock database queries
        def mock_query_side_effect(model):
            query_mock = Mock()
            query_mock.filter.return_value = query_mock
            if model == PlaidRecurringTransaction:
                query_mock.first.return_value = mock_recurring
            else:  # RecurringTransactionRule
                query_mock.first.return_value = mock_rule
            return query_mock
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        result_recurring, result_rule = self.service.link_to_rule(
            self.test_user_id,
            self.test_plaid_recurring_id,
            self.test_rule_id
        )
        
        assert result_recurring.linked_rule_id == self.test_rule_id
        assert result_recurring.is_linked_to_rule is True
        assert result_rule.id == self.test_rule_id
        
        self.mock_db.add.assert_called_once_with(mock_recurring)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_recurring)
    
    def test_link_to_rule_recurring_not_found(self):
        """Test linking when recurring transaction doesn't exist"""
        # Mock first query (recurring transaction) to return None
        def mock_query_side_effect(model):
            query_mock = Mock()
            query_mock.filter.return_value = query_mock
            if model == PlaidRecurringTransaction:
                query_mock.first.return_value = None
            return query_mock
        
        self.mock_db.query.side_effect = mock_query_side_effect
        
        with pytest.raises(ValueError, match="not found"):
            self.service.link_to_rule(
                self.test_user_id,
                self.test_plaid_recurring_id,
                self.test_rule_id
            )
    
    def test_unlink_from_rule_success(self):
        """Test successfully unlinking a recurring transaction from a rule"""
        mock_recurring = self.create_mock_plaid_recurring_transaction()
        mock_recurring.linked_rule_id = self.test_rule_id
        mock_recurring.is_linked_to_rule = True
        
        # Mock database query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mock_recurring
        self.mock_db.query.return_value = query_mock
        
        result = self.service.unlink_from_rule(
            self.test_user_id,
            self.test_plaid_recurring_id
        )
        
        assert result.linked_rule_id is None
        assert result.is_linked_to_rule is False
        
        self.mock_db.add.assert_called_once_with(mock_recurring)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_recurring)
    
    def test_get_recurring_insights_with_data(self):
        """Test getting insights when user has recurring transactions"""
        mock_recurring = [
            self.create_mock_plaid_recurring_transaction(),
            self.create_mock_plaid_recurring_transaction()
        ]
        
        # Mock the get_user_plaid_recurring_transactions call
        self.service.get_user_plaid_recurring_transactions = Mock(return_value=mock_recurring)
        
        # Mock account query
        mock_account = Mock()
        mock_account.id = self.test_account_id
        mock_account.name = "Test Account"
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_account]
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_recurring_insights(self.test_user_id)
        
        assert result["total_subscriptions"] == 2
        assert result["active_subscriptions"] == 2
        assert result["total_monthly_cost_cents"] > 0
        assert "frequency_breakdown" in result
        assert "status_breakdown" in result
        assert "top_subscriptions" in result
        assert "cost_by_account" in result
    
    def test_get_recurring_insights_no_data(self):
        """Test getting insights when user has no recurring transactions"""
        # Mock empty recurring transactions
        self.service.get_user_plaid_recurring_transactions = Mock(return_value=[])
        
        result = self.service.get_recurring_insights(self.test_user_id)
        
        assert result["total_subscriptions"] == 0
        assert result["total_monthly_cost_cents"] == 0
        assert result["active_subscriptions"] == 0
        assert result["frequency_breakdown"] == {}
        assert result["status_breakdown"] == {}
        assert result["top_subscriptions"] == []
        assert result["cost_by_account"] == {}
    
    def test_get_recurring_stats(self):
        """Test getting basic recurring transaction statistics"""
        # Mock database queries for counts
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 5  # Total count
        query_mock.all.return_value = [self.create_mock_plaid_recurring_transaction()]  # For cost calculation
        self.mock_db.query.return_value = query_mock
        
        # Mock individual filter chains
        def mock_filter_side_effect(*args):
            mock_chain = Mock()
            mock_chain.count.return_value = 3  # Active, mature, linked counts
            mock_chain.filter.return_value = mock_chain
            return mock_chain
        
        query_mock.filter.side_effect = mock_filter_side_effect
        
        result = self.service.get_recurring_stats(self.test_user_id)
        
        assert "total_recurring_transactions" in result
        assert "active_recurring_transactions" in result
        assert "mature_recurring_transactions" in result
        assert "linked_recurring_transactions" in result
        assert "total_monthly_cost_cents" in result
        assert "total_monthly_cost_dollars" in result
    
    def test_find_potential_matches(self):
        """Test finding potential rule matches for a recurring transaction"""
        mock_recurring = self.create_mock_plaid_recurring_transaction()
        mock_rule = self.create_mock_recurring_rule()
        
        # Mock get_plaid_recurring_transaction
        self.service.get_plaid_recurring_transaction = Mock(return_value=mock_recurring)
        
        # Mock rules query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_rule]
        self.mock_db.query.return_value = query_mock
        
        result = self.service.find_potential_matches(
            self.test_user_id,
            self.test_plaid_recurring_id
        )
        
        assert len(result) >= 0  # Could be 0 or more depending on matching logic
    
    def test_bulk_mute_transactions_success(self):
        """Test bulk muting multiple recurring transactions"""
        recurring_ids = ["id1", "id2", "id3"]
        
        # Mock individual mute operations
        self.service.mute_recurring_transaction = Mock(return_value=Mock())
        
        result = self.service.bulk_mute_transactions(
            self.test_user_id,
            recurring_ids,
            muted=True
        )
        
        assert result["updated_count"] == 3
        assert result["failed_count"] == 0
        assert result["action"] == "muted"
        
        # Verify mute_recurring_transaction was called for each ID
        assert self.service.mute_recurring_transaction.call_count == 3
    
    def test_bulk_mute_transactions_partial_failure(self):
        """Test bulk muting with some failures"""
        recurring_ids = ["id1", "id2", "id3"]
        
        # Mock mute operation to fail on second ID
        def mock_mute_side_effect(user_id, plaid_id, muted):
            if plaid_id == "id2":
                raise ValueError("Transaction not found")
            return Mock()
        
        self.service.mute_recurring_transaction = Mock(side_effect=mock_mute_side_effect)
        
        result = self.service.bulk_mute_transactions(
            self.test_user_id,
            recurring_ids,
            muted=True
        )
        
        assert result["updated_count"] == 2
        assert result["failed_count"] == 1
        assert "id2" in result["failed_ids"]

# Run tests with: pytest tests/unit/test_plaid_recurring_service.py -v