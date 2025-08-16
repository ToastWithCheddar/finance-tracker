"""
Integration tests for TransactionService.

These tests verify that TransactionService works correctly with a real database
and test the complete workflow including data persistence and retrieval.
"""
import pytest
from uuid import uuid4
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilter, TransactionPagination
from app.models.transaction import Transaction
from app.models.user import User
from app.models.account import Account
from app.models.category import Category


class TestTransactionServiceCreateTransactionIntegration:
    """Integration tests for transaction creation with real database."""
    
    @pytest.mark.asyncio
    async def test_create_transaction_integration_success(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test complete transaction creation flow with database."""
        # Arrange
        transaction_data = TransactionCreate(
            account_id=test_account.id,
            amount_cents=2500,
            currency="USD",
            description="Coffee purchase",
            merchant="Local Coffee Shop",
            transaction_date=date.today(),
            category_id=test_category.id,
            status="posted",
            is_recurring=False,
            is_transfer=False,
            notes="Morning coffee",
            tags=["coffee", "daily"]
        )
        
        # Act
        with patch('app.services.transaction_service.get_ml_client'):  # Skip ML for integration test
            result = await TransactionService.create_transaction(
                test_db_session, transaction_data, test_user.id
            )
        
        # Assert
        assert result is not None
        assert result.id is not None
        assert result.user_id == test_user.id
        assert result.account_id == test_account.id
        assert result.amount_cents == 2500
        assert result.currency == "USD"
        assert result.description == "Coffee purchase"
        assert result.merchant == "Local Coffee Shop"
        assert result.category_id == test_category.id
        assert result.status == "posted"
        assert result.notes == "Morning coffee"
        assert result.tags == ["coffee", "daily"]
        assert result.created_at is not None
        
        # Verify data was actually persisted
        retrieved = test_db_session.query(Transaction).filter(
            Transaction.id == result.id
        ).first()
        assert retrieved is not None
        assert retrieved.user_id == test_user.id
        assert retrieved.description == "Coffee purchase"

    @pytest.mark.asyncio
    async def test_create_transaction_with_ml_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test transaction creation with ML categorization integration."""
        # Arrange
        transaction_data = TransactionCreate(
            account_id=test_account.id,
            amount_cents=1500,
            currency="USD",
            description="Grocery shopping at Whole Foods",
            merchant="Whole Foods",
            transaction_date=date.today(),
            category_id=None,  # No category - should trigger ML
            status="posted"
        )
        
        # Mock ML service to return our test category
        mock_ml_client = AsyncMock()
        mock_ml_response = MagicMock()
        mock_ml_response.success = True
        mock_ml_response.data = MagicMock()
        mock_ml_response.data.category_id = test_category.id
        mock_ml_response.data.confidence = 0.9
        mock_ml_response.data.reasoning = "Grocery purchase detected"
        
        mock_ml_client.categorize_transaction.return_value = mock_ml_response
        
        with patch('app.services.transaction_service.get_ml_client', return_value=mock_ml_client):
            with patch('app.services.transaction_service.settings.ML_CONFIDENCE_THRESHOLD', 0.75):
                # Act
                result = await TransactionService.create_transaction(
                    test_db_session, transaction_data, test_user.id
                )
        
        # Assert
        assert result is not None
        assert result.category_id == test_category.id  # Should be set by ML
        
        # Verify ML was called correctly
        mock_ml_client.categorize_transaction.assert_called_once_with(
            description="Grocery shopping at Whole Foods",
            amount_cents=1500,
            merchant="Whole Foods",
            user_id=str(test_user.id)
        )


class TestTransactionServiceReadOperationsIntegration:
    """Integration tests for transaction read operations."""
    
    def test_get_transaction_integration(self, test_db_session, test_user, test_account):
        """Test transaction retrieval with real database."""
        # Arrange - Create a transaction directly in the database
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            amount_cents=3500,
            currency="USD",
            description="Integration test transaction",
            transaction_date=date.today(),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        test_db_session.refresh(transaction)
        
        # Act
        result = TransactionService.get_transaction(test_db_session, transaction.id, test_user.id)
        
        # Assert
        assert result is not None
        assert result.id == transaction.id
        assert result.user_id == test_user.id
        assert result.amount_cents == 3500
        assert result.description == "Integration test transaction"

    def test_get_transaction_user_isolation(self, test_db_session, test_account):
        """Test that users can only access their own transactions."""
        # Arrange - Create two users and transactions
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
        
        # Create accounts for both users
        account1 = Account(
            id=uuid4(),
            user_id=user1.id,
            name="User 1 Account",
            account_type="checking",
            balance_cents=50000,
            currency="USD",
            is_active=True
        )
        account2 = Account(
            id=uuid4(),
            user_id=user2.id,
            name="User 2 Account",
            account_type="checking",
            balance_cents=60000,
            currency="USD",
            is_active=True
        )
        test_db_session.add(account1)
        test_db_session.add(account2)
        test_db_session.commit()
        
        # Create transaction for user1
        transaction = Transaction(
            id=uuid4(),
            user_id=user1.id,
            account_id=account1.id,
            amount_cents=1000,
            currency="USD",
            description="User 1 transaction",
            transaction_date=date.today(),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        # Act - User1 should be able to access their transaction
        result1 = TransactionService.get_transaction(test_db_session, transaction.id, user1.id)
        
        # Act - User2 should NOT be able to access user1's transaction
        result2 = TransactionService.get_transaction(test_db_session, transaction.id, user2.id)
        
        # Assert
        assert result1 is not None
        assert result1.user_id == user1.id
        assert result2 is None  # User2 should not see user1's transaction

    def test_get_transactions_with_filters_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test transaction filtering with real database."""
        # Arrange - Create multiple transactions
        transactions = []
        for i in range(5):
            transaction = Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                amount_cents=(i + 1) * 1000,  # 1000, 2000, 3000, 4000, 5000
                currency="USD",
                description=f"Transaction {i + 1}",
                transaction_date=date(2025, 1, i + 1),  # Different dates
                category_id=test_category.id if i % 2 == 0 else None,  # Some with category
                status="posted"
            )
            transactions.append(transaction)
            test_db_session.add(transaction)
        
        test_db_session.commit()
        
        # Act - Filter by date range
        filters = TransactionFilter(
            start_date=date(2025, 1, 2),
            end_date=date(2025, 1, 4)
        )
        pagination = TransactionPagination(page=1, per_page=10)
        
        result_transactions, result_count = TransactionService.get_transactions_with_filters(
            test_db_session, test_user.id, filters, pagination
        )
        
        # Assert
        assert result_count == 3  # Transactions from Jan 2, 3, 4
        assert len(result_transactions) == 3
        
        # Verify transactions are in expected date range
        for transaction in result_transactions:
            assert transaction.transaction_date >= date(2025, 1, 2)
            assert transaction.transaction_date <= date(2025, 1, 4)

    def test_get_transactions_with_category_filter_integration(
        self, test_db_session, test_user, test_account, test_category
    ):
        """Test transaction filtering by category with real database."""
        # Arrange - Create transactions with and without the category
        with_category = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            amount_cents=1000,
            currency="USD",
            description="Transaction with category",
            transaction_date=date.today(),
            category_id=test_category.id,
            status="posted"
        )
        
        without_category = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            amount_cents=2000,
            currency="USD",
            description="Transaction without category",
            transaction_date=date.today(),
            category_id=None,
            status="posted"
        )
        
        test_db_session.add(with_category)
        test_db_session.add(without_category)
        test_db_session.commit()
        
        # Act - Filter by category
        filters = TransactionFilter(category_id=test_category.id)
        pagination = TransactionPagination(page=1, per_page=10)
        
        result_transactions, result_count = TransactionService.get_transactions_with_filters(
            test_db_session, test_user.id, filters, pagination
        )
        
        # Assert
        assert result_count == 1
        assert len(result_transactions) == 1
        assert result_transactions[0].category_id == test_category.id
        assert result_transactions[0].description == "Transaction with category"


class TestTransactionServiceUpdateIntegration:
    """Integration tests for transaction updates."""
    
    def test_update_transaction_integration(self, test_db_session, test_user, test_account):
        """Test transaction update with real database."""
        # Arrange - Create initial transaction
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            amount_cents=1000,
            currency="USD",
            description="Original description",
            transaction_date=date.today(),
            status="posted",
            notes="Original notes"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        test_db_session.refresh(transaction)
        
        # Act - Update the transaction
        update_data = TransactionUpdate(
            amount_cents=1500,
            description="Updated description",
            notes="Updated notes"
        )
        
        result = TransactionService.update_transaction(test_db_session, transaction, update_data)
        
        # Assert
        assert result.amount_cents == 1500
        assert result.description == "Updated description"
        assert result.notes == "Updated notes"
        assert result.updated_at is not None
        
        # Verify changes were persisted
        retrieved = test_db_session.query(Transaction).filter(
            Transaction.id == transaction.id
        ).first()
        assert retrieved.amount_cents == 1500
        assert retrieved.description == "Updated description"
        assert retrieved.notes == "Updated notes"


class TestTransactionServiceDeleteIntegration:
    """Integration tests for transaction deletion."""
    
    def test_delete_transaction_integration(self, test_db_session, test_user, test_account):
        """Test transaction deletion with real database."""
        # Arrange - Create transaction to delete
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            amount_cents=1000,
            currency="USD",
            description="Transaction to delete",
            transaction_date=date.today(),
            status="posted"
        )
        test_db_session.add(transaction)
        test_db_session.commit()
        
        transaction_id = transaction.id
        
        # Act - Delete the transaction
        result = TransactionService.delete_transaction(test_db_session, transaction)
        
        # Assert
        assert result is True
        
        # Verify transaction was actually deleted from database
        retrieved = test_db_session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        assert retrieved is None


# Test markers
pytestmark = pytest.mark.integration