"""
Integration tests for the transaction router endpoints.

These tests verify the complete HTTP request/response lifecycle for transaction endpoints,
including data validation, authentication, authorization, and proper HTTP status codes.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.services.user_service import UserService
from app.services.account_service import AccountService
from app.services.category_service import CategoryService
from app.services.transaction_service import TransactionService


class TestTransactionRouter:
    """Test suite for transaction router endpoints."""

    @pytest.fixture
    def setup_test_data(self, test_db_session: Session, authenticated_api_client: TestClient):
        """Set up test data for transaction tests."""
        # Get the authenticated user
        user_service = UserService(test_db_session)
        user = user_service.get_user_by_email("test@example.com")
        
        # Create test account
        account_service = AccountService(test_db_session)
        account_data = {
            "name": "Test Account",
            "account_type": "checking",
            "balance_cents": 100000,
            "currency": "USD"
        }
        account = account_service.create_account(user.id, account_data)
        
        # Create test category
        category_service = CategoryService(test_db_session)
        category_data = {
            "name": "Test Category",
            "description": "Test category for transactions",
            "color": "#FF6B6B",
            "emoji": "🧪"
        }
        category = category_service.create_category(user.id, category_data)
        
        return {
            "user": user,
            "account": account,
            "category": category
        }

    def test_create_transaction_success(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test successful transaction creation with valid data."""
        # Arrange
        test_data = setup_test_data
        transaction_data = {
            "account_id": str(test_data["account"].id),
            "amount_cents": 2500,
            "currency": "USD",
            "description": "API Test Transaction",
            "merchant": "Test Merchant API",
            "transaction_date": datetime.now(timezone.utc).isoformat(),
            "category_id": str(test_data["category"].id),
            "status": "completed"
        }
        
        # Act
        response = authenticated_api_client.post("/transactions", json=transaction_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["amount_cents"] == transaction_data["amount_cents"]
        assert data["description"] == transaction_data["description"]
        assert data["merchant"] == transaction_data["merchant"]
        assert data["account"]["id"] == transaction_data["account_id"]
        assert data["category"]["id"] == transaction_data["category_id"]
        
        # Verify transaction was persisted in database
        transaction_service = TransactionService(test_db_session)
        created_transaction = transaction_service.get_transaction(test_data["user"].id, data["id"])
        assert created_transaction is not None
        assert created_transaction.description == transaction_data["description"]

    def test_create_transaction_with_nonexistent_account(self, authenticated_api_client: TestClient, setup_test_data):
        """Test transaction creation failure with non-existent account."""
        # Arrange
        transaction_data = {
            "account_id": str(uuid4()),  # Non-existent account ID
            "amount_cents": 2500,
            "currency": "USD",
            "description": "Test Transaction",
            "transaction_date": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
        
        # Act
        response = authenticated_api_client.post("/transactions", json=transaction_data)
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "account" in data["detail"].lower()

    def test_create_transaction_without_auth(self, api_client: TestClient):
        """Test transaction creation failure without authentication."""
        # Arrange
        transaction_data = {
            "account_id": str(uuid4()),
            "amount_cents": 2500,
            "currency": "USD",
            "description": "Test Transaction",
            "transaction_date": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
        
        # Act
        response = api_client.post("/transactions", json=transaction_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_create_transaction_invalid_data(self, authenticated_api_client: TestClient):
        """Test transaction creation failure with invalid data."""
        # Arrange - missing required fields
        invalid_transaction_data = {
            "amount_cents": "invalid_amount",  # Invalid type
            "currency": "USD"
            # Missing required fields like account_id, description, etc.
        }
        
        # Act
        response = authenticated_api_client.post("/transactions", json=invalid_transaction_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_get_transactions_success(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test successful retrieval of user's transactions."""
        # Arrange - create test transactions
        test_data = setup_test_data
        transaction_service = TransactionService(test_db_session)
        
        # Create multiple test transactions
        for i in range(3):
            transaction_data = {
                "account_id": test_data["account"].id,
                "amount_cents": 1000 * (i + 1),
                "currency": "USD",
                "description": f"Test Transaction {i + 1}",
                "merchant": f"Test Merchant {i + 1}",
                "status": "completed"
            }
            transaction_service.create_transaction(test_data["user"].id, transaction_data)
        
        # Act
        response = authenticated_api_client.get("/transactions")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) >= 3
        
        # Verify transaction structure
        first_transaction = data["transactions"][0]
        assert "id" in first_transaction
        assert "amount_cents" in first_transaction
        assert "description" in first_transaction
        assert "account" in first_transaction
        assert "id" in first_transaction["account"]

    def test_get_transactions_with_filters(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test transaction retrieval with query filters."""
        # Arrange - create test transactions
        test_data = setup_test_data
        transaction_service = TransactionService(test_db_session)
        
        transaction_data = {
            "account_id": test_data["account"].id,
            "amount_cents": 5000,
            "currency": "USD",
            "description": "Filtered Transaction",
            "merchant": "Filter Test Merchant",
            "status": "completed"
        }
        transaction_service.create_transaction(test_data["user"].id, transaction_data)
        
        # Act - filter by description
        response = authenticated_api_client.get("/transactions?search=Filtered")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) >= 1
        
        # Verify filtered results
        filtered_transaction = data["transactions"][0]
        assert "Filtered" in filtered_transaction["description"]

    def test_get_transaction_by_id_success(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test successful retrieval of specific transaction by ID."""
        # Arrange - create test transaction
        test_data = setup_test_data
        transaction_service = TransactionService(test_db_session)
        
        transaction_data = {
            "account_id": test_data["account"].id,
            "amount_cents": 3500,
            "currency": "USD",
            "description": "Specific Transaction",
            "merchant": "Specific Merchant",
            "status": "completed"
        }
        created_transaction = transaction_service.create_transaction(test_data["user"].id, transaction_data)
        
        # Act
        response = authenticated_api_client.get(f"/transactions/{created_transaction.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_transaction.id)
        assert data["description"] == transaction_data["description"]
        assert data["amount_cents"] == transaction_data["amount_cents"]

    def test_get_transaction_not_found(self, authenticated_api_client: TestClient):
        """Test retrieval of non-existent transaction."""
        # Arrange
        non_existent_id = str(uuid4())
        
        # Act
        response = authenticated_api_client.get(f"/transactions/{non_existent_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_update_transaction_success(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test successful transaction update."""
        # Arrange - create test transaction
        test_data = setup_test_data
        transaction_service = TransactionService(test_db_session)
        
        original_data = {
            "account_id": test_data["account"].id,
            "amount_cents": 2000,
            "currency": "USD",
            "description": "Original Description",
            "merchant": "Original Merchant",
            "status": "completed"
        }
        created_transaction = transaction_service.create_transaction(test_data["user"].id, original_data)
        
        # Prepare update data
        update_data = {
            "description": "Updated Description",
            "merchant": "Updated Merchant",
            "amount_cents": 2500
        }
        
        # Act
        response = authenticated_api_client.put(f"/transactions/{created_transaction.id}", json=update_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == update_data["description"]
        assert data["merchant"] == update_data["merchant"]
        assert data["amount_cents"] == update_data["amount_cents"]
        
        # Verify update was persisted
        updated_transaction = transaction_service.get_transaction(test_data["user"].id, created_transaction.id)
        assert updated_transaction.description == update_data["description"]

    def test_delete_transaction_success(self, authenticated_api_client: TestClient, test_db_session: Session, setup_test_data):
        """Test successful transaction deletion."""
        # Arrange - create test transaction
        test_data = setup_test_data
        transaction_service = TransactionService(test_db_session)
        
        transaction_data = {
            "account_id": test_data["account"].id,
            "amount_cents": 1500,
            "currency": "USD",
            "description": "Transaction to Delete",
            "merchant": "Delete Test Merchant",
            "status": "completed"
        }
        created_transaction = transaction_service.create_transaction(test_data["user"].id, transaction_data)
        
        # Act
        response = authenticated_api_client.delete(f"/transactions/{created_transaction.id}")
        
        # Assert
        assert response.status_code == 204
        
        # Verify transaction was deleted
        deleted_transaction = transaction_service.get_transaction(test_data["user"].id, created_transaction.id)
        assert deleted_transaction is None

    def test_delete_transaction_not_found(self, authenticated_api_client: TestClient):
        """Test deletion of non-existent transaction."""
        # Arrange
        non_existent_id = str(uuid4())
        
        # Act
        response = authenticated_api_client.delete(f"/transactions/{non_existent_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_user_data_isolation(self, api_client: TestClient, test_db_session: Session):
        """Test that users cannot access other users' transactions."""
        # Arrange - create two different users
        user_service = UserService(test_db_session)
        account_service = AccountService(test_db_session)
        transaction_service = TransactionService(test_db_session)
        
        # User 1
        user1_data = {"email": "user1@test.com", "password": "Password123!", "display_name": "User 1"}
        user1 = user_service.create_user(user1_data)
        account1_data = {"name": "User1 Account", "account_type": "checking", "balance_cents": 50000, "currency": "USD"}
        account1 = account_service.create_account(user1.id, account1_data)
        transaction1_data = {"account_id": account1.id, "amount_cents": 1000, "currency": "USD", "description": "User1 Transaction", "status": "completed"}
        transaction1 = transaction_service.create_transaction(user1.id, transaction1_data)
        
        # User 2 - login as this user
        user2_data = {"email": "user2@test.com", "password": "Password123!", "display_name": "User 2"}
        user2 = user_service.create_user(user2_data)
        
        # Login as User 2
        login_data = {"username": user2_data["email"], "password": user2_data["password"]}
        login_response = api_client.post("/auth/login", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Create authenticated client for User 2
        user2_client = TestClient(authenticated_api_client.app)
        user2_client.headers["Authorization"] = f"Bearer {token}"
        
        # Act - User 2 tries to access User 1's transaction
        response = user2_client.get(f"/transactions/{transaction1.id}")
        
        # Assert
        assert response.status_code == 404  # Should not find the transaction (data isolation)
        data = response.json()
        assert "detail" in data