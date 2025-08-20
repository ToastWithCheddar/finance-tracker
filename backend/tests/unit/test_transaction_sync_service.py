"""
Unit tests for TransactionSyncService conflict resolution functionality.

These tests focus on testing the conflict resolution logic that detects and merges
potential duplicates between manually-entered and Plaid-imported transactions.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any

from app.services.transaction_sync_service import TransactionSyncService
from app.models.transaction import Transaction
from app.models.account import Account


class TestTransactionConflictResolution:
    """Test the conflict resolution functionality for transaction sync."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.sync_service = TransactionSyncService()
        self.mock_db = MagicMock()
        
        # Create mock account
        self.mock_account = Account(
            id=uuid4(),
            name="Test Checking",
            account_type="checking",
            user_id=uuid4()
        )
        
        # Sample Plaid transaction data
        self.sample_plaid_transaction = {
            'transaction_id': 'plaid_12345',
            'name': 'STARBUCKS #123',
            'amount': 10.55,  # Plaid amount (positive for expenses in checking accounts)
            'date': '2025-08-15',
            'category': ['Food and Drink', 'Coffee'],
            'merchant_name': 'Starbucks'
        }
    
    def test_find_potential_duplicate_exact_match(self):
        """Test successful duplicate detection with exact match."""
        # Arrange
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,  # Manual entry: $10.55 expense (negative)
            description="Starbucks Coffee",
            merchant="Starbucks",
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,  # Manual transaction
            status='posted'
        )
        
        # Mock database query
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        # Mock the normalize method on the sync service directly
        with patch.object(self.sync_service, '_normalize_merchant_name', side_effect=lambda desc, merchant=None: "starbucks"):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result == existing_transaction
        assert self.mock_db.query.called
        
        # Verify query parameters
        call_args = self.mock_db.query.return_value.filter.call_args[0]
        # Should filter by account_id, plaid_transaction_id IS NULL, date range, amount range
        assert len(call_args) == 5
    
    def test_find_potential_duplicate_amount_tolerance(self):
        """Test duplicate detection with amount within tolerance."""
        # Arrange - Manual transaction $10.50, Plaid transaction $10.55 (within $1 tolerance)
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1050,  # $10.50 expense
            description="Starbucks",
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result == existing_transaction
    
    def test_find_potential_duplicate_date_tolerance(self):
        """Test duplicate detection with date within tolerance."""
        # Arrange - Manual transaction on 2025-08-14, Plaid transaction on 2025-08-15 (within 2 days)
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Starbucks",
            transaction_date=date(2025, 8, 14),  # One day earlier
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result == existing_transaction
    
    def test_find_potential_duplicate_no_match_amount_out_of_tolerance(self):
        """Test no duplicate found when amount is outside tolerance."""
        # Arrange - Manual transaction $8.55, Plaid transaction $10.55 (>$1 difference)
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-855,  # $8.55 expense - outside $1 tolerance
            description="Starbucks",
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result is None  # Amount outside tolerance should not match
    
    def test_find_potential_duplicate_no_match_date_out_of_tolerance(self):
        """Test no duplicate found when date is outside tolerance."""
        # Arrange - Manual transaction on 2025-08-12, Plaid transaction on 2025-08-15 (3 days, >2 day tolerance)
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Starbucks",
            transaction_date=date(2025, 8, 12),  # 3 days earlier - outside tolerance
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result is None  # Date outside tolerance should not match
    
    def test_find_potential_duplicate_no_match_description_similarity_too_low(self):
        """Test no duplicate found when description similarity is too low."""
        # Arrange
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="McDonald's",  # Different merchant
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', 
                         side_effect=lambda desc, merchant=None: {
                             "STARBUCKS #123": "starbucks",
                             "McDonald's": "mcdonalds"
                         }.get(desc, desc.lower())):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result is None  # Low similarity should not match
    
    def test_find_potential_duplicate_excludes_plaid_transactions(self):
        """Test that only manual transactions (plaid_transaction_id IS NULL) are considered."""
        # Arrange
        existing_plaid_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Starbucks",
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id="existing_plaid_123",  # Already has Plaid ID
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_plaid_transaction]
        
        # Act
        result = self.sync_service._find_potential_duplicate(
            self.mock_db, self.mock_account, self.sample_plaid_transaction
        )
        
        # Assert
        assert result is None  # Should not match transactions that already have Plaid IDs
    
    @pytest.mark.asyncio
    async def test_create_transaction_from_plaid_with_merge(self):
        """Test transaction creation with successful merge of existing manual transaction."""
        # Arrange
        existing_manual_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Starbucks Coffee",
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='pending',
            metadata_json={}
        )
        
        # Mock _find_potential_duplicate to return the existing transaction
        with patch.object(self.sync_service, '_find_potential_duplicate', return_value=existing_manual_transaction):
            with patch.object(self.sync_service, '_parse_date', return_value=datetime(2025, 8, 15, tzinfo=timezone.utc)):
                
                # Act
                result = await self.sync_service._create_transaction_from_plaid(
                    self.sample_plaid_transaction, self.mock_account, self.mock_db
                )
        
        # Assert
        assert result == existing_manual_transaction
        assert result.plaid_transaction_id == 'plaid_12345'
        assert result.status == 'posted'  # Should be updated from 'pending'
        assert result.metadata_json['sync_match'] == 'merged_from_plaid_import'
        assert 'match_timestamp' in result.metadata_json
        assert 'original_plaid_data' in result.metadata_json
        
        # Verify database operations
        self.mock_db.add.assert_called_once_with(existing_manual_transaction)
    
    @pytest.mark.asyncio
    async def test_create_transaction_from_plaid_no_merge_creates_new(self):
        """Test transaction creation when no duplicate is found (normal creation)."""
        # Arrange
        # Mock _find_potential_duplicate to return None (no duplicate)
        with patch.object(self.sync_service, '_find_potential_duplicate', return_value=None):
            with patch.object(self.sync_service, '_parse_date', return_value=datetime(2025, 8, 15, tzinfo=timezone.utc)):
                with patch.object(self.sync_service, '_convert_plaid_amount', return_value=-1055):
                    with patch('app.services.transaction_sync_service.TransactionService') as mock_transaction_service:
                        mock_service_instance = mock_transaction_service.return_value
                        mock_new_transaction = Transaction(id=uuid4())
                        mock_service_instance.create_transaction.return_value = mock_new_transaction
                        
                        # Act
                        result = await self.sync_service._create_transaction_from_plaid(
                            self.sample_plaid_transaction, self.mock_account, self.mock_db
                        )
        
        # Assert
        assert result == mock_new_transaction
        # Verify new transaction was created through TransactionService
        mock_service_instance.create_transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_merges_with_existing_manual_transaction_integration(self):
        """Integration test: Full sync process that merges with existing manual transaction."""
        # Arrange
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1050,  # $10.50
            description="Starbucks",
            transaction_date=date(2025, 8, 14),  # One day earlier
            plaid_transaction_id=None,
            status='posted'
        )
        
        plaid_transactions = [self.sample_plaid_transaction]
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # No existing Plaid transaction IDs
            [existing_transaction]  # Potential duplicate found
        ]
        
        # Mock other dependencies
        with patch.object(self.sync_service, '_parse_date', return_value=datetime(2025, 8, 15, tzinfo=timezone.utc)):
            with patch.object(self.sync_service, '_convert_plaid_amount', return_value=-1055):
                with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
                    
                    # Act
                    result = await self.sync_service._process_account_transactions(
                        self.mock_account, plaid_transactions, self.mock_db
                    )
        
        # Assert
        assert result.new_transactions == 0  # No new transactions created
        assert result.updated_transactions == 1  # One transaction merged
        assert result.duplicates_skipped == 0
        assert len(result.errors) == 0
        
        # Verify the merge occurred
        assert existing_transaction.plaid_transaction_id == 'plaid_12345'
    
    @pytest.mark.asyncio 
    async def test_sync_creates_new_transaction_when_no_match_integration(self):
        """Integration test: Full sync process that creates new transaction when no duplicate found."""
        # Arrange
        plaid_transactions = [self.sample_plaid_transaction]
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # No existing Plaid transaction IDs
            []   # No potential duplicates found
        ]
        
        # Mock other dependencies
        with patch.object(self.sync_service, '_parse_date', return_value=datetime(2025, 8, 15, tzinfo=timezone.utc)):
            with patch.object(self.sync_service, '_convert_plaid_amount', return_value=-1055):
                with patch('app.services.transaction_sync_service.TransactionService') as mock_transaction_service:
                    mock_service_instance = mock_transaction_service.return_value
                    mock_new_transaction = Transaction(
                        id=uuid4(),
                        plaid_transaction_id='plaid_12345'
                    )
                    mock_service_instance.create_transaction.return_value = mock_new_transaction
                    
                    # Act
                    result = await self.sync_service._process_account_transactions(
                        self.mock_account, plaid_transactions, self.mock_db
                    )
        
        # Assert
        assert result.new_transactions == 1  # One new transaction created
        assert result.updated_transactions == 0  # No transactions merged
        assert result.duplicates_skipped == 0
        assert len(result.errors) == 0
    
    def test_find_potential_duplicate_partial_description_match(self):
        """Test duplicate detection with partial description matching."""
        # Arrange
        existing_transaction = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="STARBUCKS COFFEE",  # Similar but not exact
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [existing_transaction]
        
        with patch.object(self.sync_service, '_normalize_merchant_name', return_value="starbucks"):
            # Both normalize to "starbucks" - should match
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result == existing_transaction
    
    def test_find_potential_duplicate_multiple_candidates_best_match(self):
        """Test duplicate detection chooses best match when multiple candidates exist."""
        # Arrange
        candidate1 = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Coffee Shop",  # Lower similarity
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        candidate2 = Transaction(
            id=uuid4(),
            user_id=self.mock_account.user_id,
            account_id=self.mock_account.id,
            amount_cents=-1055,
            description="Starbucks Store",  # Higher similarity
            transaction_date=date(2025, 8, 15),
            plaid_transaction_id=None,
            status='posted'
        )
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [candidate1, candidate2]
        
        def normalize_side_effect(desc, merchant=None):
            normalize_map = {
                "STARBUCKS #123": "starbucks",
                "Coffee Shop": "coffee shop",
                "Starbucks Store": "starbucks store"
            }
            return normalize_map.get(desc, desc.lower())
        
        with patch.object(self.sync_service, '_normalize_merchant_name', side_effect=normalize_side_effect):
            
            # Act
            result = self.sync_service._find_potential_duplicate(
                self.mock_db, self.mock_account, self.sample_plaid_transaction
            )
        
        # Assert
        assert result == candidate2  # Should choose the better match


# Marker for unit tests
pytestmark = pytest.mark.unit