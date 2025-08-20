"""
Unit tests for TransactionService.

These tests focus on testing the business logic of TransactionService 
in isolation by mocking all external dependencies including the database.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilter, TransactionPagination
from app.models.transaction import Transaction
from fastapi import HTTPException


class TestTransactionServiceCreateTransaction:
    """Test the create_transaction method."""
    
    @pytest.mark.asyncio
    async def test_create_transaction_success_without_ml(self, mocker):
        """Test successful transaction creation without ML categorization."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        transaction_data = TransactionCreate(
            account_id=uuid4(),
            amount_cents=2500,
            currency="USD",
            description="Test transaction",
            merchant="Test Store",
            transaction_date=date.today(),
            category_id=uuid4(),  # Category provided, so ML won't be called
            status="posted",
            is_recurring=False,
            is_transfer=False,
            notes="Test notes",
            tags=["test"]
        )
        
        # Mock the database transaction creation
        mock_transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            **transaction_data.model_dump()
        )
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock the Transaction constructor
        mocker.patch('app.services.transaction_service.Transaction', return_value=mock_transaction)
        
        # Act
        result = await TransactionService.create_transaction(mock_db, transaction_data, user_id)
        
        # Assert
        assert result == mock_transaction
        assert result.user_id == user_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_transaction_with_ml_categorization(self, mocker):
        """Test transaction creation with ML categorization when no category provided."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        predicted_category_id = uuid4()
        
        transaction_data = TransactionCreate(
            account_id=uuid4(),
            amount_cents=2500,
            currency="USD",
            description="Coffee at Starbucks",
            merchant="Starbucks",
            transaction_date=date.today(),
            category_id=None,  # No category provided, should trigger ML
            status="posted"
        )
        
        # Mock ML service
        mock_ml_client = AsyncMock()
        mock_ml_response = MagicMock()
        mock_ml_response.success = True
        mock_ml_response.data = MagicMock()
        mock_ml_response.data.category_id = predicted_category_id
        mock_ml_response.data.confidence = 0.85
        mock_ml_response.data.reasoning = "High confidence food purchase"
        
        mock_ml_client.categorize_transaction.return_value = mock_ml_response
        mocker.patch('app.services.transaction_service.get_ml_client', return_value=mock_ml_client)
        mocker.patch('app.services.transaction_service.settings.ML_CONFIDENCE_THRESHOLD', 0.75)
        
        mock_transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            **transaction_data.model_dump()
        )
        mock_transaction.category_id = predicted_category_id
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mocker.patch('app.services.transaction_service.Transaction', return_value=mock_transaction)
        
        # Act
        result = await TransactionService.create_transaction(mock_db, transaction_data, user_id)
        
        # Assert
        assert result == mock_transaction
        mock_ml_client.categorize_transaction.assert_called_once_with(
            description="Coffee at Starbucks",
            amount_cents=2500,
            merchant="Starbucks",
            user_id=str(user_id)
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_transaction_ml_low_confidence(self, mocker):
        """Test transaction creation when ML has low confidence."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        transaction_data = TransactionCreate(
            account_id=uuid4(),
            amount_cents=2500,
            currency="USD",
            description="Unclear transaction",
            transaction_date=date.today(),
            category_id=None,  # No category provided
            status="posted"
        )
        
        # Mock ML service with low confidence
        mock_ml_client = AsyncMock()
        mock_ml_response = MagicMock()
        mock_ml_response.success = True
        mock_ml_response.data = MagicMock()
        mock_ml_response.data.confidence = 0.45  # Low confidence
        
        mock_ml_client.categorize_transaction.return_value = mock_ml_response
        mocker.patch('app.services.transaction_service.get_ml_client', return_value=mock_ml_client)
        mocker.patch('app.services.transaction_service.settings.ML_CONFIDENCE_THRESHOLD', 0.75)
        
        mock_transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            **transaction_data.model_dump()
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mocker.patch('app.services.transaction_service.Transaction', return_value=mock_transaction)
        
        # Act
        result = await TransactionService.create_transaction(mock_db, transaction_data, user_id)
        
        # Assert
        assert result == mock_transaction
        assert result.category_id is None  # Should remain None due to low confidence
        mock_ml_client.categorize_transaction.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_transaction_ml_service_failure(self, mocker):
        """Test transaction creation when ML service fails gracefully."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        transaction_data = TransactionCreate(
            account_id=uuid4(),
            amount_cents=2500,
            currency="USD",
            description="Test transaction",
            transaction_date=date.today(),
            category_id=None,
            status="posted"
        )
        
        # Mock ML service failure
        mock_ml_client = AsyncMock()
        mock_ml_response = MagicMock()
        mock_ml_response.success = False
        mock_ml_response.error = MagicMock()
        mock_ml_response.error.message = "ML service unavailable"
        
        mock_ml_client.categorize_transaction.return_value = mock_ml_response
        mocker.patch('app.services.transaction_service.get_ml_client', return_value=mock_ml_client)
        
        mock_transaction = Transaction(
            id=uuid4(),
            user_id=user_id,
            **transaction_data.model_dump()
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mocker.patch('app.services.transaction_service.Transaction', return_value=mock_transaction)
        
        # Act - Should not raise exception, just log warning
        result = await TransactionService.create_transaction(mock_db, transaction_data, user_id)
        
        # Assert
        assert result == mock_transaction
        assert result.category_id is None  # Should remain None due to ML failure
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestTransactionServiceGetTransaction:
    """Test the get_transaction method."""
    
    def test_get_transaction_success(self, mocker):
        """Test successful transaction retrieval."""
        # Arrange
        mock_db = MagicMock()
        transaction_id = uuid4()
        user_id = uuid4()
        
        mock_transaction = Transaction(
            id=transaction_id,
            user_id=user_id,
            amount_cents=2500,
            description="Test transaction"
        )
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = mock_transaction
        
        # Act
        result = TransactionService.get_transaction(mock_db, transaction_id, user_id)
        
        # Assert
        assert result == mock_transaction
        mock_db.query.assert_called_once_with(Transaction)
        mock_query.filter.assert_called_once()

    def test_get_transaction_not_found(self, mocker):
        """Test transaction not found scenario."""
        # Arrange
        mock_db = MagicMock()
        transaction_id = uuid4()
        user_id = uuid4()
        
        mock_query = mock_db.query.return_value
        mock_query.filter.return_value.first.return_value = None
        
        # Act
        result = TransactionService.get_transaction(mock_db, transaction_id, user_id)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once_with(Transaction)


class TestTransactionServiceGetTransactionsWithFilters:
    """Test the get_transactions_with_filters method."""
    
    def test_get_transactions_with_filters_success(self, mocker):
        """Test successful transactions retrieval with filters."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        filters = TransactionFilter(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            category_id=uuid4()
        )
        pagination = TransactionPagination(page=1, per_page=25)
        
        mock_transactions = [
            Transaction(id=uuid4(), user_id=user_id, amount_cents=1000),
            Transaction(id=uuid4(), user_id=user_id, amount_cents=2000),
        ]
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_transactions
        mock_query.count.return_value = 2
        
        # Mock joinedload
        mocker.patch('app.services.transaction_service.joinedload')
        
        # Act
        result_transactions, result_count = TransactionService.get_transactions_with_filters(
            mock_db, user_id, filters, pagination
        )
        
        # Assert
        assert result_transactions == mock_transactions
        assert result_count == 2
        mock_db.query.assert_called_with(Transaction)
        
        # Verify filters were applied (multiple filter calls)
        assert mock_query.filter.call_count >= 3  # user_id + start_date + end_date + category_id

    def test_get_transactions_empty_result(self, mocker):
        """Test transactions retrieval with no results."""
        # Arrange
        mock_db = MagicMock()
        user_id = uuid4()
        
        filters = TransactionFilter()
        pagination = TransactionPagination(page=1, per_page=25)
        
        mock_query = mock_db.query.return_value
        mock_query.options.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        mocker.patch('app.services.transaction_service.joinedload')
        
        # Act
        result_transactions, result_count = TransactionService.get_transactions_with_filters(
            mock_db, user_id, filters, pagination
        )
        
        # Assert
        assert result_transactions == []
        assert result_count == 0


class TestTransactionServiceUpdateTransaction:
    """Test the update_transaction method."""
    
    def test_update_transaction_success(self, mocker):
        """Test successful transaction update."""
        # Arrange
        mock_db = MagicMock()
        
        original_transaction = Transaction(
            id=uuid4(),
            amount_cents=1000,
            description="Original transaction",
            notes="Original notes"
        )
        
        update_data = TransactionUpdate(
            amount_cents=1500,
            description="Updated transaction",
            notes="Updated notes"
        )
        
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Act
        result = TransactionService.update_transaction(mock_db, original_transaction, update_data)
        
        # Assert
        assert result == original_transaction
        assert result.amount_cents == 1500
        assert result.description == "Updated transaction"
        assert result.notes == "Updated notes"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(original_transaction)

    def test_update_transaction_partial_update(self, mocker):
        """Test partial transaction update (only some fields)."""
        # Arrange
        mock_db = MagicMock()
        
        original_transaction = Transaction(
            id=uuid4(),
            amount_cents=1000,
            description="Original transaction",
            notes="Original notes"
        )
        
        update_data = TransactionUpdate(
            amount_cents=1500  # Only updating amount
        )
        
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Act
        result = TransactionService.update_transaction(mock_db, original_transaction, update_data)
        
        # Assert
        assert result == original_transaction
        assert result.amount_cents == 1500
        assert result.description == "Original transaction"  # Should remain unchanged
        assert result.notes == "Original notes"  # Should remain unchanged
        mock_db.commit.assert_called_once()


class TestTransactionServiceDeleteTransaction:
    """Test the delete_transaction method."""
    
    def test_delete_transaction_success(self, mocker):
        """Test successful transaction deletion."""
        # Arrange
        mock_db = MagicMock()
        
        transaction = Transaction(
            id=uuid4(),
            amount_cents=1000,
            description="Transaction to delete"
        )
        
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None
        
        # Act
        result = TransactionService.delete_transaction(mock_db, transaction)
        
        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(transaction)
        mock_db.commit.assert_called_once()


# Integration test marker
pytestmark = pytest.mark.unit