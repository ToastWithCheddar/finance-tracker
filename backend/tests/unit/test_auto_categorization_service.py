"""
Unit tests for AutoCategorizationService
Tests the rule matching and application logic in isolation
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.auto_categorization_service import AutoCategorizationService
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.models.account import Account

class TestAutoCategorizationService:
    """Test AutoCategorizationService functionality"""
    
    def setup_method(self):
        """Setup test dependencies"""
        self.mock_db = Mock()
        self.service = AutoCategorizationService(self.mock_db)
        
        # Test data
        self.test_user_id = uuid4()
        self.test_category_id = uuid4()
        self.test_account_id = uuid4()
    
    def create_mock_rule(self, priority=100, conditions=None, actions=None):
        """Create a mock categorization rule"""
        if conditions is None:
            conditions = {
                "merchant_contains": ["starbucks"],
                "amount_range": {"min_cents": 100, "max_cents": 2000}
            }
        
        if actions is None:
            actions = {
                "set_category_id": str(self.test_category_id),
                "set_confidence": 0.9
            }
        
        rule = Mock(spec=CategorizationRule)
        rule.id = uuid4()
        rule.name = "Test Rule"
        rule.priority = priority
        rule.conditions = conditions
        rule.actions = actions
        rule.is_active = True
        rule.times_applied = 0
        rule.last_applied_at = None
        
        # Mock the matching methods
        rule.matches_merchant = Mock(return_value=True)
        rule.matches_description = Mock(return_value=True)
        rule.matches_amount = Mock(return_value=True)
        rule.matches_account_type = Mock(return_value=True)
        rule.matches_transaction_type = Mock(return_value=True)
        rule.matches_account_id = Mock(return_value=True)
        rule.exclude_category = Mock(return_value=False)
        rule.get_target_category_id = Mock(return_value=self.test_category_id)
        rule.get_confidence_score = Mock(return_value=0.9)
        rule.get_tags_to_add = Mock(return_value=["coffee"])
        rule.get_note_to_add = Mock(return_value=None)
        rule.increment_application_count = Mock()
        
        return rule
    
    def create_mock_transaction(self, merchant="Starbucks", amount_cents=500):
        """Create a mock transaction"""
        transaction = Mock(spec=Transaction)
        transaction.id = uuid4()
        transaction.merchant = merchant
        transaction.description = f"Purchase at {merchant}"
        transaction.amount_cents = amount_cents
        transaction.transaction_type = "expense"
        transaction.account_id = self.test_account_id
        transaction.category_id = None
        transaction.tags = []
        transaction.notes = None
        transaction.is_manually_categorized = False
        
        # Mock account
        account = Mock(spec=Account)
        account.account_type = "checking"
        transaction.account = account
        
        return transaction
    
    def test_get_user_rules_caching(self):
        """Test that user rules are cached properly"""
        # Mock database query
        mock_rules = [self.create_mock_rule()]
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_rules
        
        # First call should query database
        rules1 = self.service._get_user_rules(self.test_user_id)
        assert rules1 == mock_rules
        
        # Second call should use cache (no additional query)
        rules2 = self.service._get_user_rules(self.test_user_id)
        assert rules2 == mock_rules
        
        # Verify only one database query was made
        assert self.mock_db.query.call_count == 1
    
    def test_rule_matches_transaction_all_conditions_pass(self):
        """Test that rule matching works when all conditions pass"""
        rule = self.create_mock_rule()
        transaction = self.create_mock_transaction()
        
        result = self.service._rule_matches_transaction(rule, transaction)
        
        assert result is True
        rule.matches_merchant.assert_called_once()
        rule.matches_description.assert_called_once()
        rule.matches_amount.assert_called_once()
        rule.matches_account_type.assert_called_once()
        rule.matches_transaction_type.assert_called_once()
        rule.matches_account_id.assert_called_once()
        rule.exclude_category.assert_called_once()
    
    def test_rule_matches_transaction_merchant_fails(self):
        """Test that rule matching fails when merchant condition fails"""
        rule = self.create_mock_rule()
        rule.matches_merchant.return_value = False
        transaction = self.create_mock_transaction()
        
        result = self.service._rule_matches_transaction(rule, transaction)
        
        assert result is False
        rule.matches_merchant.assert_called_once()
        # Other conditions should not be checked after first failure
        rule.matches_description.assert_not_called()
    
    def test_apply_rule_actions_category_change(self):
        """Test applying rule actions changes transaction category"""
        rule = self.create_mock_rule()
        transaction = self.create_mock_transaction()
        
        changes = self.service._apply_rule_actions(rule, transaction)
        
        assert transaction.category_id == self.test_category_id
        assert transaction.ml_confidence == 0.9
        assert transaction.is_manually_categorized is False
        assert "category_id" in changes
        assert "ml_confidence" in changes
        assert "auto_categorized" in changes
    
    def test_apply_rule_actions_add_tags(self):
        """Test applying rule actions adds tags to transaction"""
        rule = self.create_mock_rule()
        rule.get_tags_to_add.return_value = ["coffee", "beverage"]
        transaction = self.create_mock_transaction()
        transaction.tags = ["existing"]
        
        changes = self.service._apply_rule_actions(rule, transaction)
        
        expected_tags = ["existing", "coffee", "beverage"]
        assert set(transaction.tags) == set(expected_tags)
        assert "tags" in changes
    
    def test_apply_rules_to_transaction_success(self):
        """Test successful rule application to a transaction"""
        # Setup mocks
        rule = self.create_mock_rule()
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]
        
        transaction = self.create_mock_transaction()
        
        result = self.service.apply_rules_to_transaction(transaction, self.test_user_id)
        
        assert result["success"] is True
        assert result["rule_applied"] is True
        assert result["rule_id"] == str(rule.id)
        assert result["rule_name"] == rule.name
        assert "changes" in result
        
        # Verify rule application was tracked
        rule.increment_application_count.assert_called_once()
        self.mock_db.add.assert_called()
        self.mock_db.commit.assert_called()
    
    def test_apply_rules_to_transaction_no_matching_rules(self):
        """Test rule application when no rules match"""
        # Setup mocks - return empty rules list
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        transaction = self.create_mock_transaction()
        
        result = self.service.apply_rules_to_transaction(transaction, self.test_user_id)
        
        assert result["success"] is True
        assert result["rule_applied"] is False
        assert result["message"] == "No active rules found"
    
    def test_apply_rules_to_transaction_dry_run(self):
        """Test rule application in dry run mode"""
        rule = self.create_mock_rule()
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]
        
        transaction = self.create_mock_transaction()
        
        result = self.service.apply_rules_to_transaction(transaction, self.test_user_id, dry_run=True)
        
        assert result["success"] is True
        assert result["rule_applied"] is True
        assert result["dry_run"] is True
        
        # Verify no changes were committed in dry run
        rule.increment_application_count.assert_not_called()
        self.mock_db.add.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_batch_apply_rules_success(self):
        """Test batch rule application to multiple transactions"""
        # Setup mocks
        rule = self.create_mock_rule()
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [rule]
        
        transaction1 = self.create_mock_transaction("Starbucks", 500)
        transaction2 = self.create_mock_transaction("Coffee Bean", 600)
        transactions = [transaction1, transaction2]
        
        # Mock transaction query
        self.mock_db.query.return_value.filter.return_value.all.return_value = transactions
        
        transaction_ids = [t.id for t in transactions]
        
        result = self.service.batch_apply_rules(transaction_ids, self.test_user_id)
        
        assert result["success"] is True
        assert result["transactions_processed"] == 2
        assert result["rules_applied"] == 2
        assert len(result["results"]) == 2
        
        # Verify both transactions were processed
        for transaction_result in result["results"]:
            assert transaction_result["rule_applied"] is True
    
    def test_rule_priority_ordering(self):
        """Test that rules are applied in priority order"""
        # Create rules with different priorities
        high_priority_rule = self.create_mock_rule(priority=10)
        low_priority_rule = self.create_mock_rule(priority=100)
        
        # Mock query to return rules in database order (not priority order)
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            low_priority_rule, high_priority_rule
        ]
        
        transaction = self.create_mock_transaction()
        
        result = self.service.apply_rules_to_transaction(transaction, self.test_user_id)
        
        # High priority rule should be applied first
        assert result["rule_id"] == str(high_priority_rule.id)
    
    def test_test_rule_against_transactions(self):
        """Test testing rule conditions against historical transactions"""
        # Mock transaction query
        mock_transactions = [
            self.create_mock_transaction("Starbucks", 500),
            self.create_mock_transaction("Coffee Bean", 600),
            self.create_mock_transaction("McDonalds", 400)  # Should not match coffee rule
        ]
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_transactions
        
        conditions = {
            "merchant_contains": ["starbucks", "coffee"]
        }
        
        # Mock the rule matching to return True for coffee shops, False for McDonalds
        with pytest.MonkeyPatch.context() as mp:
            def mock_rule_matches(rule, transaction):
                if "coffee" in transaction.merchant.lower() or "starbucks" in transaction.merchant.lower():
                    return True
                return False
            
            mp.setattr(self.service, '_rule_matches_transaction', mock_rule_matches)
            
            result = self.service.test_rule_against_transactions(conditions, self.test_user_id)
        
        # Should match 2 out of 3 transactions
        assert len(result) == 2
    
    def test_clear_rule_cache(self):
        """Test that rule cache can be cleared"""
        # Setup cache
        cache_key = f"user_rules_{self.test_user_id}"
        self.service._rule_cache[cache_key] = [self.create_mock_rule()]
        self.service._cache_last_updated[cache_key] = datetime.now(timezone.utc)
        
        # Clear cache for specific user
        self.service.clear_rule_cache(self.test_user_id)
        
        assert cache_key not in self.service._rule_cache
        assert cache_key not in self.service._cache_last_updated
    
    def test_get_matching_statistics(self):
        """Test getting rule matching statistics"""
        # Mock rules with different application counts
        rule1 = self.create_mock_rule()
        rule1.times_applied = 10
        rule1.success_rate = 0.8
        
        rule2 = self.create_mock_rule()
        rule2.times_applied = 0
        rule2.success_rate = None
        
        rule3 = self.create_mock_rule()
        rule3.times_applied = 5
        rule3.success_rate = 0.9
        
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            rule1, rule2, rule3
        ]
        
        result = self.service.get_matching_statistics(self.test_user_id)
        
        assert result["total_rules"] == 3
        assert result["active_rules"] == 3
        assert result["total_applications"] == 15  # 10 + 0 + 5
        assert result["rules_never_used"] == 1
        assert result["average_success_rate"] == 0.85  # (0.8 + 0.9) / 2
        assert result["most_used_rule"]["times_applied"] == 10

# Run tests with: pytest tests/unit/test_auto_categorization_service.py -v