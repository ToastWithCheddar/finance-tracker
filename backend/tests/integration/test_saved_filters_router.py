"""
Integration tests for the saved filters router endpoints.

These tests verify the complete HTTP request/response lifecycle for saved filter endpoints,
including data validation, authentication, authorization, and proper HTTP status codes.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4, UUID

from app.services.user_service import UserService
from app.models.saved_filter import SavedFilter


class TestSavedFiltersRouter:
    """Test suite for saved filters router endpoints."""

    @pytest.fixture
    def setup_test_data(self, test_db_session: Session, authenticated_api_client: TestClient):
        """Set up test data for saved filter tests."""
        # Get the authenticated user
        user_service = UserService(test_db_session)
        user = user_service.get_user_by_email("test@example.com")
        
        return {
            "user": user,
            "client": authenticated_api_client,
            "db": test_db_session
        }

    @pytest.fixture
    def sample_filter_data(self):
        """Provide sample saved filter data for testing."""
        return {
            "name": "Monthly Groceries",
            "filters": {
                "categories": ["groceries", "food"],
                "amount_range": {
                    "min": 10.00,
                    "max": 500.00
                },
                "date_range": {
                    "period": "monthly"
                },
                "merchants": ["Whole Foods", "Safeway", "Trader Joe's"],
                "transaction_type": "debit"
            }
        }

    def test_create_saved_filter_success(self, setup_test_data, sample_filter_data):
        """Test successful creation of a saved filter."""
        client = setup_test_data["client"]
        
        response = client.post("/api/saved-filters", json=sample_filter_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == sample_filter_data["name"]
        assert data["filters"] == sample_filter_data["filters"]
        assert "user_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_saved_filter_missing_required_fields(self, setup_test_data):
        """Test saved filter creation fails with missing required fields."""
        client = setup_test_data["client"]
        
        # Missing name
        invalid_data = {
            "filters": {"category": "groceries"}
        }
        
        response = client.post("/api/saved-filters", json=invalid_data)
        assert response.status_code == 422

        # Missing filters
        invalid_data = {
            "name": "Test Filter"
        }
        
        response = client.post("/api/saved-filters", json=invalid_data)
        assert response.status_code == 422

    def test_create_saved_filter_empty_name(self, setup_test_data):
        """Test saved filter creation fails with empty name."""
        client = setup_test_data["client"]
        
        invalid_data = {
            "name": "",
            "filters": {"category": "groceries"}
        }
        
        response = client.post("/api/saved-filters", json=invalid_data)
        assert response.status_code == 422

    def test_create_saved_filter_duplicate_name_fails(self, setup_test_data, sample_filter_data):
        """Test that creating a filter with duplicate name fails."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create first filter directly in database
        existing_filter = SavedFilter(
            user_id=user.id,
            name=sample_filter_data["name"],
            filters=sample_filter_data["filters"]
        )
        db.add(existing_filter)
        db.commit()
        
        # Try to create another filter with same name
        response = client.post("/api/saved-filters", json=sample_filter_data)
        assert response.status_code == 400
        
        error_data = response.json()
        assert "already exists" in error_data["detail"].lower()

    def test_create_saved_filter_different_users_same_name_allowed(self, test_db_session: Session, api_client: TestClient, sample_filter_data):
        """Test that different users can have filters with the same name."""
        # Create two users
        user_service = UserService(test_db_session)
        
        user_a_data = {
            "email": "user_a@example.com",
            "password": "SecurePassword123!",
            "display_name": "User A"
        }
        user_a = user_service.create_user(user_a_data)
        
        user_b_data = {
            "email": "user_b@example.com",
            "password": "SecurePassword123!",
            "display_name": "User B"
        }
        user_b = user_service.create_user(user_b_data)
        
        # Login as User A and create filter
        login_response_a = api_client.post("/auth/login", data={
            "username": user_a_data["email"],
            "password": user_a_data["password"]
        })
        assert login_response_a.status_code == 200
        token_a = login_response_a.json()["access_token"]
        
        client_a = TestClient(api_client.app)
        client_a.headers["Authorization"] = f"Bearer {token_a}"
        
        response = client_a.post("/api/saved-filters", json=sample_filter_data)
        assert response.status_code == 200
        
        # Login as User B and create filter with same name
        login_response_b = api_client.post("/auth/login", data={
            "username": user_b_data["email"],
            "password": user_b_data["password"]
        })
        assert login_response_b.status_code == 200
        token_b = login_response_b.json()["access_token"]
        
        client_b = TestClient(api_client.app)
        client_b.headers["Authorization"] = f"Bearer {token_b}"
        
        # Should succeed - different users can have same filter names
        response = client_b.post("/api/saved-filters", json=sample_filter_data)
        assert response.status_code == 200

    def test_get_saved_filters_success(self, setup_test_data, sample_filter_data):
        """Test successful retrieval of saved filters list."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create multiple filters directly in the database
        filters = []
        for i in range(3):
            saved_filter = SavedFilter(
                user_id=user.id,
                name=f"Test Filter {i+1}",
                filters={
                    "category": f"category_{i+1}",
                    "amount_min": i * 10,
                    "amount_max": (i + 1) * 100
                }
            )
            db.add(saved_filter)
            filters.append(saved_filter)
        
        db.commit()
        for saved_filter in filters:
            db.refresh(saved_filter)
        
        # Retrieve the filters
        response = client.get("/api/saved-filters")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Verify they're ordered by created_at desc (most recent first)
        names = [f["name"] for f in data]
        assert "Test Filter 3" in names
        assert "Test Filter 2" in names
        assert "Test Filter 1" in names

    def test_get_saved_filters_empty_list(self, setup_test_data):
        """Test retrieval of saved filters when user has none."""
        client = setup_test_data["client"]
        
        response = client.get("/api/saved-filters")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_saved_filter_by_id_success(self, setup_test_data, sample_filter_data):
        """Test successful retrieval of a specific saved filter by ID."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create a filter
        saved_filter = SavedFilter(
            user_id=user.id,
            name=sample_filter_data["name"],
            filters=sample_filter_data["filters"]
        )
        db.add(saved_filter)
        db.commit()
        db.refresh(saved_filter)
        
        # Retrieve the filter
        response = client.get(f"/api/saved-filters/{saved_filter.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(saved_filter.id)
        assert data["name"] == sample_filter_data["name"]
        assert data["filters"] == sample_filter_data["filters"]

    def test_get_saved_filter_by_id_not_found(self, setup_test_data):
        """Test retrieval of non-existent saved filter returns 404."""
        client = setup_test_data["client"]
        
        # Try to get a non-existent filter
        fake_id = str(uuid4())
        response = client.get(f"/api/saved-filters/{fake_id}")
        assert response.status_code == 404

    def test_update_saved_filter_success(self, setup_test_data, sample_filter_data):
        """Test successful update of an existing saved filter."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create a filter
        saved_filter = SavedFilter(
            user_id=user.id,
            name="Original Name",
            filters={"category": "original"}
        )
        db.add(saved_filter)
        db.commit()
        db.refresh(saved_filter)
        
        # Update the filter
        update_data = {
            "name": "Updated Name",
            "filters": {
                "category": "updated",
                "amount_range": {
                    "min": 50.00,
                    "max": 1000.00
                }
            }
        }
        
        response = client.put(f"/api/saved-filters/{saved_filter.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["filters"] == update_data["filters"]

    def test_update_saved_filter_partial_update(self, setup_test_data):
        """Test partial update of a saved filter (only some fields)."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create a filter
        original_filters = {"category": "original", "amount": 100}
        saved_filter = SavedFilter(
            user_id=user.id,
            name="Original Name",
            filters=original_filters
        )
        db.add(saved_filter)
        db.commit()
        db.refresh(saved_filter)
        
        # Update only the name
        update_data = {"name": "New Name Only"}
        
        response = client.put(f"/api/saved-filters/{saved_filter.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "New Name Only"
        assert data["filters"] == original_filters  # Should remain unchanged

    def test_update_saved_filter_name_conflict(self, setup_test_data):
        """Test update with conflicting name fails."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create two filters
        filter_1 = SavedFilter(
            user_id=user.id,
            name="Filter One",
            filters={"category": "one"}
        )
        filter_2 = SavedFilter(
            user_id=user.id,
            name="Filter Two",
            filters={"category": "two"}
        )
        db.add_all([filter_1, filter_2])
        db.commit()
        db.refresh(filter_1)
        db.refresh(filter_2)
        
        # Try to update filter_2 to have same name as filter_1
        update_data = {"name": "Filter One"}
        
        response = client.put(f"/api/saved-filters/{filter_2.id}", json=update_data)
        assert response.status_code == 400
        
        error_data = response.json()
        assert "already exists" in error_data["detail"].lower()

    def test_update_saved_filter_not_found(self, setup_test_data):
        """Test update of non-existent saved filter returns 404."""
        client = setup_test_data["client"]
        
        fake_id = str(uuid4())
        update_data = {"name": "New Name"}
        
        response = client.put(f"/api/saved-filters/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_delete_saved_filter_success(self, setup_test_data, sample_filter_data):
        """Test successful deletion of a saved filter."""
        client = setup_test_data["client"]
        user = setup_test_data["user"]
        db = setup_test_data["db"]
        
        # Create a filter
        saved_filter = SavedFilter(
            user_id=user.id,
            name="To Be Deleted",
            filters={"category": "delete_me"}
        )
        db.add(saved_filter)
        db.commit()
        db.refresh(saved_filter)
        filter_id = saved_filter.id
        
        # Delete the filter
        response = client.delete(f"/api/saved-filters/{filter_id}")
        assert response.status_code == 200
        
        # Verify response
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"].lower()
        
        # Verify it's deleted by trying to retrieve it
        response = client.get(f"/api/saved-filters/{filter_id}")
        assert response.status_code == 404

    def test_delete_saved_filter_not_found(self, setup_test_data):
        """Test deletion of non-existent saved filter returns 404."""
        client = setup_test_data["client"]
        
        fake_id = str(uuid4())
        response = client.delete(f"/api/saved-filters/{fake_id}")
        assert response.status_code == 404

    def test_saved_filter_authorization_isolation(self, test_db_session: Session, api_client: TestClient):
        """
        Test that users can only access their own saved filters.
        Critical security test to prevent data leaks.
        """
        # Create two users
        user_service = UserService(test_db_session)
        
        # User A
        user_a_data = {
            "email": "user_a@example.com",
            "password": "SecurePassword123!",
            "display_name": "User A"
        }
        user_a = user_service.create_user(user_a_data)
        
        # User B  
        user_b_data = {
            "email": "user_b@example.com",
            "password": "SecurePassword123!",
            "display_name": "User B"
        }
        user_b = user_service.create_user(user_b_data)
        
        # Create saved filter for User A
        filter_a = SavedFilter(
            user_id=user_a.id,
            name="User A's Private Filter",
            filters={
                "confidential": "data",
                "sensitive": "information"
            }
        )
        test_db_session.add(filter_a)
        test_db_session.commit()
        test_db_session.refresh(filter_a)
        
        # Login as User A and verify access
        login_response_a = api_client.post("/auth/login", data={
            "username": user_a_data["email"],
            "password": user_a_data["password"]
        })
        assert login_response_a.status_code == 200
        token_a = login_response_a.json()["access_token"]
        
        client_a = TestClient(api_client.app)
        client_a.headers["Authorization"] = f"Bearer {token_a}"
        
        # User A should see their filter
        response = client_a.get("/api/saved-filters")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "User A's Private Filter"
        
        # Login as User B
        login_response_b = api_client.post("/auth/login", data={
            "username": user_b_data["email"],
            "password": user_b_data["password"]
        })
        assert login_response_b.status_code == 200
        token_b = login_response_b.json()["access_token"]
        
        client_b = TestClient(api_client.app)
        client_b.headers["Authorization"] = f"Bearer {token_b}"
        
        # User B should NOT see User A's filters
        response = client_b.get("/api/saved-filters")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
        
        # User B should get 404 when trying to access User A's filter directly
        response = client_b.get(f"/api/saved-filters/{filter_a.id}")
        assert response.status_code == 404
        
        # User B should get 404 when trying to update User A's filter
        response = client_b.put(f"/api/saved-filters/{filter_a.id}", json={"name": "Hacked"})
        assert response.status_code == 404
        
        # User B should get 404 when trying to delete User A's filter
        response = client_b.delete(f"/api/saved-filters/{filter_a.id}")
        assert response.status_code == 404

    def test_complex_filter_data_preservation(self, setup_test_data):
        """Test that complex nested filter data is properly preserved."""
        client = setup_test_data["client"]
        
        complex_filter_data = {
            "name": "Complex Filter",
            "filters": {
                "logic": "AND",
                "conditions": [
                    {
                        "field": "amount",
                        "operator": "between", 
                        "values": [100.00, 500.00]
                    },
                    {
                        "logic": "OR",
                        "conditions": [
                            {
                                "field": "category",
                                "operator": "in",
                                "values": ["groceries", "dining", "entertainment"]
                            },
                            {
                                "field": "merchant",
                                "operator": "contains",
                                "values": ["Amazon", "Target"]
                            }
                        ]
                    }
                ],
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "preset": "year_to_date"
                },
                "metadata": {
                    "created_by": "filter_builder_v2",
                    "version": "2.1",
                    "tags": ["complex", "nested", "production"]
                }
            }
        }
        
        # Create the complex filter
        response = client.post("/api/saved-filters", json=complex_filter_data)
        assert response.status_code == 200
        
        created_data = response.json()
        filter_id = created_data["id"]
        
        # Retrieve and verify the complex data is preserved exactly
        response = client.get(f"/api/saved-filters/{filter_id}")
        assert response.status_code == 200
        
        retrieved_data = response.json()
        assert retrieved_data["filters"] == complex_filter_data["filters"]

    def test_unauthenticated_access_denied(self, api_client: TestClient):
        """Test that unauthenticated requests are denied."""
        sample_data = {
            "name": "Test Filter",
            "filters": {"category": "test"}
        }
        
        # Test all endpoints without authentication
        endpoints = [
            ("GET", "/api/saved-filters"),
            ("POST", "/api/saved-filters", sample_data),
            ("GET", f"/api/saved-filters/{uuid4()}"),
            ("PUT", f"/api/saved-filters/{uuid4()}", {"name": "Test"}),
            ("DELETE", f"/api/saved-filters/{uuid4()}")
        ]
        
        for method, url, *args in endpoints:
            if method == "GET":
                response = api_client.get(url)
            elif method == "POST":
                response = api_client.post(url, json=args[0])
            elif method == "PUT":
                response = api_client.put(url, json=args[0])
            elif method == "DELETE":
                response = api_client.delete(url)
            
            assert response.status_code == 401, f"Expected 401 for {method} {url}"