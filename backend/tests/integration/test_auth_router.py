"""
Integration tests for the authentication router endpoints.

These tests verify the complete HTTP request/response lifecycle for auth endpoints,
including data validation, authentication flow, and proper HTTP status codes.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.user_service import UserService


class TestAuthRouter:
    """Test suite for authentication router endpoints."""

    def test_register_user_success(self, api_client: TestClient, test_db_session: Session):
        """Test successful user registration with valid data."""
        # Arrange
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "display_name": "New Test User"
        }
        
        # Act
        response = api_client.post("/auth/register", json=registration_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert "token_type" in data
        assert data["user"]["email"] == registration_data["email"]
        assert data["user"]["display_name"] == registration_data["display_name"]
        assert data["token_type"] == "bearer"
        
        # Verify user was persisted in database
        user_service = UserService(test_db_session)
        created_user = user_service.get_user_by_email(registration_data["email"])
        assert created_user is not None
        assert created_user.email == registration_data["email"]

    def test_register_duplicate_email_failure(self, api_client: TestClient, test_db_session: Session):
        """Test registration failure with duplicate email."""
        # Arrange - create existing user
        existing_user_data = {
            "email": "duplicate@example.com",
            "password": "Password123!",
            "display_name": "Existing User"
        }
        user_service = UserService(test_db_session)
        user_service.create_user(existing_user_data)
        
        # Try to register with same email
        duplicate_data = {
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
            "display_name": "Duplicate User"
        }
        
        # Act
        response = api_client.post("/auth/register", json=duplicate_data)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    def test_register_invalid_email_format(self, api_client: TestClient):
        """Test registration failure with invalid email format."""
        # Arrange
        invalid_data = {
            "email": "invalid-email-format",
            "password": "SecurePassword123!",
            "display_name": "Test User"
        }
        
        # Act
        response = api_client.post("/auth/register", json=invalid_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_register_weak_password(self, api_client: TestClient):
        """Test registration failure with weak password."""
        # Arrange
        weak_password_data = {
            "email": "test@example.com",
            "password": "weak",
            "display_name": "Test User"
        }
        
        # Act
        response = api_client.post("/auth/register", json=weak_password_data)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "password" in data["detail"].lower()

    def test_login_success(self, api_client: TestClient, test_db_session: Session):
        """Test successful login with correct credentials."""
        # Arrange - create test user
        user_data = {
            "email": "login@example.com",
            "password": "LoginPassword123!",
            "display_name": "Login Test User"
        }
        user_service = UserService(test_db_session)
        user_service.create_user(user_data)
        
        # Prepare login data
        login_data = {
            "username": user_data["email"],  # OAuth2 form uses 'username'
            "password": user_data["password"]
        }
        
        # Act
        response = api_client.post("/auth/login", data=login_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_invalid_email(self, api_client: TestClient):
        """Test login failure with non-existent email."""
        # Arrange
        invalid_login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        
        # Act
        response = api_client.post("/auth/login", data=invalid_login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "credentials" in data["detail"].lower()

    def test_login_wrong_password(self, api_client: TestClient, test_db_session: Session):
        """Test login failure with wrong password."""
        # Arrange - create test user
        user_data = {
            "email": "wrongpass@example.com",
            "password": "CorrectPassword123!",
            "display_name": "Wrong Pass Test User"
        }
        user_service = UserService(test_db_session)
        user_service.create_user(user_data)
        
        # Try with wrong password
        wrong_login_data = {
            "username": user_data["email"],
            "password": "WrongPassword123!"
        }
        
        # Act
        response = api_client.post("/auth/login", data=wrong_login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "credentials" in data["detail"].lower()

    def test_login_missing_credentials(self, api_client: TestClient):
        """Test login failure with missing credentials."""
        # Act - login with no data
        response = api_client.post("/auth/login", data={})
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_get_current_user_with_valid_token(self, authenticated_api_client: TestClient):
        """Test retrieving current user with valid authentication token."""
        # Act
        response = authenticated_api_client.get("/auth/me")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "display_name" in data
        assert data["email"] == "test@example.com"

    def test_get_current_user_without_token(self, api_client: TestClient):
        """Test accessing protected endpoint without authentication token."""
        # Act
        response = api_client.get("/auth/me")
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_get_current_user_with_invalid_token(self, api_client: TestClient):
        """Test accessing protected endpoint with invalid token."""
        # Arrange
        api_client.headers["Authorization"] = "Bearer invalid_token_here"
        
        # Act
        response = api_client.get("/auth/me")
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data