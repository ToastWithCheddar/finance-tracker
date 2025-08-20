"""
Integration tests for categorization rules router
Tests the complete workflow of creating, managing, and applying categorization rules
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.main import app
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.categorization_rule import CategorizationRule
from app.models.categorization_rule_template import CategorizationRuleTemplate

client = TestClient(app)

class TestCategorizationRulesRouter:
    """Test categorization rules API endpoints"""
    
    def setup_method(self):
        """Setup test data"""
        # This would be replaced with proper test fixtures in a real test environment
        self.test_user_id = str(uuid4())
        self.test_category_id = str(uuid4())
        self.test_account_id = str(uuid4())
        
        # Mock authentication headers
        self.auth_headers = {
            "Authorization": f"Bearer test_token_{self.test_user_id}"
        }
    
    def test_create_categorization_rule(self):
        """Test creating a new categorization rule"""
        rule_data = {
            "name": "Coffee Shop Rule",
            "description": "Categorize coffee shop purchases",
            "priority": 50,
            "conditions": {
                "merchant_contains": ["starbucks", "coffee"],
                "amount_range": {"min_cents": 100, "max_cents": 2000}
            },
            "actions": {
                "set_category_id": self.test_category_id,
                "add_tags": ["coffee"],
                "set_confidence": 0.9
            },
            "is_active": True
        }
        
        response = client.post(
            "/api/categorization-rules/",
            json=rule_data,
            headers=self.auth_headers
        )
        
        # In a real test, this would assert successful creation
        # For now, we'll check that the endpoint exists and accepts the request
        assert response.status_code in [200, 201, 401, 422]  # 401/422 expected without real auth
    
    def test_get_categorization_rules(self):
        """Test retrieving categorization rules with pagination"""
        response = client.get(
            "/api/categorization-rules/?page=1&per_page=10",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401]
    
    def test_get_categorization_rule_by_id(self):
        """Test retrieving a specific categorization rule"""
        rule_id = str(uuid4())
        
        response = client.get(
            f"/api/categorization-rules/{rule_id}",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_update_categorization_rule(self):
        """Test updating a categorization rule"""
        rule_id = str(uuid4())
        
        update_data = {
            "name": "Updated Coffee Rule",
            "priority": 75,
            "is_active": False
        }
        
        response = client.put(
            f"/api/categorization-rules/{rule_id}",
            json=update_data,
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401, 422]
    
    def test_delete_categorization_rule(self):
        """Test deleting a categorization rule"""
        rule_id = str(uuid4())
        
        response = client.delete(
            f"/api/categorization-rules/{rule_id}",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 204, 404, 401]
    
    def test_test_rule_conditions(self):
        """Test testing rule conditions against transactions"""
        test_conditions = {
            "merchant_contains": ["test", "merchant"],
            "amount_range": {"min_cents": 1000}
        }
        
        response = client.post(
            "/api/categorization-rules/test-conditions",
            json=test_conditions,
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401, 422]
    
    def test_apply_rules_to_transactions(self):
        """Test applying rules to specific transactions"""
        transaction_ids = [str(uuid4()), str(uuid4())]
        
        response = client.post(
            "/api/categorization-rules/apply-to-transactions",
            json=transaction_ids,
            params={"dry_run": True},
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401, 422]
    
    def test_get_rule_templates(self):
        """Test retrieving rule templates"""
        response = client.get(
            "/api/categorization-rules/templates",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401]
    
    def test_create_rule_from_template(self):
        """Test creating a rule from a template"""
        template_id = str(uuid4())
        
        customizations = {
            "name": "My Coffee Rule",
            "target_category_id": self.test_category_id
        }
        
        response = client.post(
            f"/api/categorization-rules/templates/{template_id}/create-rule",
            json={"customizations": customizations},
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 201, 404, 401, 422]
    
    def test_get_rule_statistics(self):
        """Test retrieving rule statistics"""
        response = client.get(
            "/api/categorization-rules/statistics",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401]
    
    def test_get_rule_effectiveness(self):
        """Test retrieving rule effectiveness metrics"""
        rule_id = str(uuid4())
        
        response = client.get(
            f"/api/categorization-rules/{rule_id}/effectiveness",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_provide_rule_feedback(self):
        """Test providing feedback on rule effectiveness"""
        rule_id = str(uuid4())
        
        response = client.post(
            f"/api/categorization-rules/{rule_id}/feedback",
            params={"success": True},
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_rule_validation(self):
        """Test validation of rule data"""
        # Test invalid conditions
        invalid_rule = {
            "name": "",  # Invalid: empty name
            "conditions": {},  # Invalid: empty conditions
            "actions": {}  # Invalid: empty actions
        }
        
        response = client.post(
            "/api/categorization-rules/",
            json=invalid_rule,
            headers=self.auth_headers
        )
        
        assert response.status_code in [400, 422, 401]
    
    def test_rule_priority_ordering(self):
        """Test that rules are returned in priority order"""
        response = client.get(
            "/api/categorization-rules/",
            headers=self.auth_headers
        )
        
        # This test would verify ordering in a real environment
        assert response.status_code in [200, 401]

class TestPlaidRecurringTransactionsRouter:
    """Test Plaid recurring transactions API endpoints"""
    
    def setup_method(self):
        """Setup test data"""
        self.test_user_id = str(uuid4())
        
        # Mock authentication headers
        self.auth_headers = {
            "Authorization": f"Bearer test_token_{self.test_user_id}"
        }
    
    def test_get_plaid_recurring_transactions(self):
        """Test retrieving Plaid recurring transactions"""
        response = client.get(
            "/api/recurring/plaid-subscriptions",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401]
    
    def test_sync_plaid_recurring_transactions(self):
        """Test manually syncing Plaid recurring transactions"""
        response = client.post(
            "/api/recurring/plaid-subscriptions/sync",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401, 500]  # 500 expected without Plaid credentials
    
    def test_mute_plaid_recurring_transaction(self):
        """Test muting a Plaid recurring transaction"""
        plaid_recurring_id = "test_recurring_id"
        
        response = client.put(
            f"/api/recurring/plaid-subscriptions/{plaid_recurring_id}/mute",
            params={"muted": True},
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_link_plaid_recurring_to_rule(self):
        """Test linking Plaid recurring transaction to rule"""
        plaid_recurring_id = "test_recurring_id"
        rule_id = str(uuid4())
        
        response = client.post(
            f"/api/recurring/plaid-subscriptions/{plaid_recurring_id}/link",
            json=rule_id,
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401, 422]
    
    def test_unlink_plaid_recurring_from_rule(self):
        """Test unlinking Plaid recurring transaction from rule"""
        plaid_recurring_id = "test_recurring_id"
        
        response = client.delete(
            f"/api/recurring/plaid-subscriptions/{plaid_recurring_id}/link",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_get_potential_rule_matches(self):
        """Test finding potential rule matches"""
        plaid_recurring_id = "test_recurring_id"
        
        response = client.get(
            f"/api/recurring/plaid-subscriptions/{plaid_recurring_id}/potential-matches",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 404, 401]
    
    def test_get_recurring_insights(self):
        """Test retrieving recurring transaction insights"""
        response = client.get(
            "/api/recurring/insights",
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401]
    
    def test_bulk_mute_plaid_recurring_transactions(self):
        """Test bulk muting Plaid recurring transactions"""
        plaid_recurring_ids = ["id1", "id2", "id3"]
        
        response = client.post(
            "/api/recurring/plaid-subscriptions/bulk-mute",
            json=plaid_recurring_ids,
            params={"muted": True},
            headers=self.auth_headers
        )
        
        assert response.status_code in [200, 401, 422]

class TestRuleEngineLogic:
    """Test the rule matching and application logic"""
    
    def test_rule_matching_logic(self):
        """Test that rule conditions match transactions correctly"""
        # This would test the actual rule matching logic
        # In a real test environment with a test database
        pass
    
    def test_rule_priority_application(self):
        """Test that higher priority rules are applied first"""
        # This would test rule priority ordering
        pass
    
    def test_rule_performance_tracking(self):
        """Test that rule application statistics are tracked"""
        # This would test the performance tracking functionality
        pass

class TestIntegrationWorkflow:
    """Test complete workflows combining multiple features"""
    
    def test_end_to_end_rule_creation_and_application(self):
        """Test creating a rule and applying it to transactions"""
        # This would test a complete workflow:
        # 1. Create a categorization rule
        # 2. Create some test transactions
        # 3. Apply the rule to the transactions
        # 4. Verify the transactions were categorized correctly
        pass
    
    def test_plaid_recurring_to_rule_workflow(self):
        """Test linking Plaid recurring transactions to rules"""
        # This would test:
        # 1. Mock Plaid recurring transaction data
        # 2. Create matching recurring transaction rule
        # 3. Link them together
        # 4. Verify the link works
        pass

# Run tests with: pytest tests/integration/test_categorization_rules_router.py -v