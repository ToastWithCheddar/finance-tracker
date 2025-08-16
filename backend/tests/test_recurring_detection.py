# Standard library imports
import pytest
from datetime import date, timedelta
from uuid import uuid4

# Third-party imports
from sqlalchemy.orm import Session

# Local imports
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransactionRule, FrequencyType
from app.services.recurring_detection_service import RecurringDetectionService

class TestRecurringDetectionService:
    """Test suite for the RecurringDetectionService."""
    
    def test_detect_monthly_pattern(self, db: Session):
        """Test detection of monthly recurring pattern."""
        # Create test user and account
        user = User(
            email="test@example.com",
            supabase_user_id=uuid4()
        )
        db.add(user)
        db.flush()
        
        account = Account(
            user_id=user.id,
            name="Test Account",
            account_type="checking",
            balance_cents=100000
        )
        db.add(account)
        db.flush()
        
        # Create monthly recurring transactions (Netflix-like pattern)
        base_date = date.today() - timedelta(days=90)
        amounts = [1299, 1299, 1299]  # $12.99 each
        
        for i, amount in enumerate(amounts):
            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                amount_cents=amount,
                description="NETFLIX.COM",
                merchant="Netflix",
                transaction_date=base_date + timedelta(days=30 * i),
                status="posted"
            )
            db.add(transaction)
        
        db.commit()
        
        # Test pattern detection
        service = RecurringDetectionService(db)
        patterns = service.detect_patterns_for_user(user.id)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.frequency == FrequencyType.MONTHLY
        assert pattern.confidence_score > 0.5
        assert abs(pattern.avg_amount_cents - 1299) < 50  # Close to $12.99
        assert "netflix" in pattern.normalized_merchant.lower()
    
    def test_detect_weekly_pattern(self, db: Session):
        """Test detection of weekly recurring pattern."""
        # Create test user and account
        user = User(
            email="test2@example.com",
            supabase_user_id=uuid4()
        )
        db.add(user)
        db.flush()
        
        account = Account(
            user_id=user.id,
            name="Test Account",
            account_type="checking"
        )
        db.add(account)
        db.flush()
        
        # Create weekly recurring transactions
        base_date = date.today() - timedelta(days=28)
        amounts = [2500, 2500, 2500, 2500]  # $25.00 each week
        
        for i, amount in enumerate(amounts):
            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                amount_cents=amount,
                description="WEEKLY GROCERIES",
                merchant="Grocery Store",
                transaction_date=base_date + timedelta(days=7 * i),
                status="posted"
            )
            db.add(transaction)
        
        db.commit()
        
        # Test pattern detection
        service = RecurringDetectionService(db)
        patterns = service.detect_patterns_for_user(user.id)
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.frequency == FrequencyType.WEEKLY
        assert pattern.confidence_score > 0.5
        assert abs(pattern.avg_amount_cents - 2500) < 100
    
    def test_get_suggestions_excludes_existing_rules(self, db: Session):
        """Test that suggestions exclude patterns with existing rules."""
        # Create test user and account
        user = User(
            email="test3@example.com",
            supabase_user_id=uuid4()
        )
        db.add(user)
        db.flush()
        
        account = Account(
            user_id=user.id,
            name="Test Account",
            account_type="checking"
        )
        db.add(account)
        db.flush()
        
        # Create recurring transactions
        base_date = date.today() - timedelta(days=90)
        for i in range(3):
            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                amount_cents=1299,
                description="NETFLIX.COM",
                merchant="Netflix",
                transaction_date=base_date + timedelta(days=30 * i),
                status="posted"
            )
            db.add(transaction)
        
        # Create an existing rule for this pattern
        rule = RecurringTransactionRule(
            user_id=user.id,
            account_id=account.id,
            name="Netflix Subscription",
            description="NETFLIX.COM",
            amount_cents=1299,
            frequency=FrequencyType.MONTHLY,
            start_date=base_date,
            next_due_date=date.today() + timedelta(days=30),
            is_active=True,
            is_confirmed=True
        )
        db.add(rule)
        db.commit()
        
        # Test suggestions
        service = RecurringDetectionService(db)
        suggestions = service.get_suggestions_for_user(user.id)
        
        # Should not suggest pattern that already has a rule
        assert len(suggestions) == 0
    
    def test_create_rule_from_suggestion(self, db: Session):
        """Test creating a rule from a suggestion."""
        # Create test user and account
        user = User(
            email="test4@example.com",
            supabase_user_id=uuid4()
        )
        db.add(user)
        db.flush()
        
        account = Account(
            user_id=user.id,
            name="Test Account",
            account_type="checking"
        )
        db.add(account)
        db.flush()
        
        db.commit()
        
        # Create a mock suggestion
        suggestion = {
            'merchant': 'Spotify Premium',
            'amount_cents': 999,
            'currency': 'USD',
            'frequency': 'monthly',
            'interval': 1,
            'confidence_score': 0.85,
            'account_id': account.id,
            'category_id': None,
            'transaction_count': 3,
            'next_expected_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        # Test rule creation
        service = RecurringDetectionService(db)
        rule = service.create_rule_from_suggestion(user.id, suggestion)
        
        assert rule.user_id == user.id
        assert rule.account_id == account.id
        assert rule.amount_cents == 999
        assert rule.frequency == FrequencyType.MONTHLY
        assert rule.is_confirmed is True
        assert rule.detection_method == "ml_pattern"
        assert "Spotify Premium" in rule.description