"""
Test configuration and fixtures for the Finance Tracker backend.

This module provides shared fixtures for unit and integration testing,
including database setup, authentication, and common test data.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import Goal
from app.services.user_service import UserService


@pytest.fixture(scope="function")
def test_db_session() -> Session:
    """
    Create an isolated in-memory SQLite database session for each test function.
    
    This fixture ensures complete test isolation by creating a fresh database
    for each test. All tables are created at the start and dropped at the end.
    
    Returns:
        Session: SQLAlchemy session connected to test database
    """
    # Create in-memory SQLite database with connection pooling
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,  # Set to True for SQL debugging
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,  # Allow multi-threading
        },
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine
    )
    db = SessionLocal()
    
    try:
        yield db
    finally:
        # Clean up
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db_session: Session) -> User:
    """
    Create a test user in the database.
    
    Args:
        test_db_session: Database session fixture
        
    Returns:
        User: Created test user
    """
    user = User(
        id=uuid4(),
        email="test@example.com",
        display_name="Test User",
        locale="en-US",
        timezone="UTC",
        currency="USD",
        is_active=True,
        avatar_url=None
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def test_account(test_db_session: Session, test_user: User) -> Account:
    """
    Create a test account for the test user.
    
    Args:
        test_db_session: Database session fixture
        test_user: Test user fixture
        
    Returns:
        Account: Created test account
    """
    account = Account(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Checking Account",
        account_type="checking",
        balance_cents=100000,  # $1000.00
        currency="USD",
        is_active=True,
        institution_name="Test Bank",
        last_four="1234"
    )
    test_db_session.add(account)
    test_db_session.commit()
    test_db_session.refresh(account)
    return account


@pytest.fixture
def test_category(test_db_session: Session, test_user: User) -> Category:
    """
    Create a test category for the test user.
    
    Args:
        test_db_session: Database session fixture
        test_user: Test user fixture
        
    Returns:
        Category: Created test category
    """
    category = Category(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Category",
        description="Test category for testing",
        emoji="🧪",
        color="#FF6B6B",
        is_system=False,
        is_active=True,
        sort_order=1
    )
    test_db_session.add(category)
    test_db_session.commit()
    test_db_session.refresh(category)
    return category


@pytest.fixture
def sample_transaction_data() -> dict:
    """
    Provide sample transaction data for testing.
    
    Returns:
        dict: Sample transaction data
    """
    return {
        "amount_cents": 2500,  # $25.00
        "currency": "USD",
        "description": "Test Transaction",
        "merchant": "Test Merchant",
        "transaction_date": datetime.now(timezone.utc).date(),
        "status": "completed",
        "is_recurring": False,
        "is_transfer": False,
        "notes": "Test transaction for testing",
        "tags": ["test", "sample"]
    }


@pytest.fixture
def sample_budget_data() -> dict:
    """
    Provide sample budget data for testing.
    
    Returns:
        dict: Sample budget data
    """
    return {
        "name": "Test Budget",
        "amount_cents": 50000,  # $500.00
        "period": "monthly",
        "start_date": datetime.now(timezone.utc).date(),
        "alert_threshold": 0.8,  # 80%
        "is_active": True
    }


@pytest.fixture
def sample_goal_data() -> dict:
    """
    Provide sample goal data for testing.
    
    Returns:
        dict: Sample goal data
    """
    return {
        "name": "Test Savings Goal",
        "description": "Save money for testing",
        "target_amount_cents": 100000,  # $1000.00
        "goal_type": "savings",
        "priority": "medium",
        "status": "active",
        "monthly_target_cents": 10000,  # $100.00
        "auto_contribute": False,
        "milestone_percentage": 25
    }


# Async fixtures for async tests
@pytest.fixture
async def async_test_db_session():
    """
    Async version of test_db_session for async tests.
    Note: This is a placeholder - in a real implementation you'd use
    asyncpg and async SQLAlchemy for proper async database testing.
    """
    # For now, we'll use the sync version since our services are mostly sync
    # In a full async implementation, you'd use:
    # - asyncpg instead of sqlite
    # - async SQLAlchemy session
    # - async context managers
    pass


@pytest.fixture(scope="module")
def api_client():
    """
    Create FastAPI TestClient for API testing.
    
    Returns:
        TestClient: FastAPI test client
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def authenticated_api_client(test_db_session: Session, api_client: TestClient):
    """
    Create authenticated API client with valid JWT token.
    
    Args:
        test_db_session: Database session fixture
        api_client: FastAPI test client
        
    Returns:
        TestClient: Authenticated FastAPI test client
    """
    # 1. Create a user directly in the test DB
    user_data = {
        "email": "test@example.com",
        "password": "SecureTestPassword123!",
        "display_name": "Test User"
    }
    
    # Use UserService to create user with proper password hashing
    user_service = UserService(test_db_session)
    user = user_service.create_user(user_data)
    
    # 2. Use the regular client to log in and get a token
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = api_client.post("/auth/login", data=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    
    # 3. Create new client with auth header
    authenticated_client = TestClient(app)
    authenticated_client.headers["Authorization"] = f"Bearer {token}"
    
    yield authenticated_client


# Markers for test organization
pytestmark = pytest.mark.unit  # Default marker for all tests in this conftest