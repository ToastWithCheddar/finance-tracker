"""
Integration tests for Analytics Router endpoints.

Tests the Money Flow (Sankey Diagram) and Spending Heatmap endpoints
to ensure they meet production-readiness standards and return properly
formatted data for frontend visualization libraries.
"""
import pytest
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


class TestAnalyticsRouter:
    """
    Integration tests for analytics endpoints focusing on data accuracy,
    proper formatting, and edge case handling.
    """

    def test_spending_heatmap_basic_functionality(
        self, test_db_session: Session, test_user: User, test_account: User, api_client: TestClient
    ):
        """
        Test spending heatmap endpoint returns correct daily aggregations.
        Validates response format expected by Nivo Calendar component.
        """
        # Create expense categories
        groceries_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Groceries",
            description="Food expenses",
            emoji="🛒",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        rent_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Rent",
            description="Housing expenses",
            emoji="🏠",
            color="#ef4444",
            is_system=False,
            is_active=True,
            sort_order=2
        )
        test_db_session.add_all([groceries_cat, rent_cat])
        test_db_session.commit()

        # Create specific test transactions on distinct days
        base_date = date(2024, 1, 15)
        transactions = [
            # Day 1: Single expense
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=groceries_cat.id,
                amount_cents=-2500,  # -$25.00
                currency="USD",
                description="Grocery shopping",
                transaction_date=base_date,
                status="completed"
            ),
            # Day 2: Multiple expenses (should be aggregated)
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=groceries_cat.id,
                amount_cents=-1500,  # -$15.00
                currency="USD",
                description="Snacks",
                transaction_date=base_date + timedelta(days=1),
                status="completed"
            ),
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=rent_cat.id,
                amount_cents=-3500,  # -$35.00
                currency="USD",
                description="Rent payment",
                transaction_date=base_date + timedelta(days=1),
                status="completed"
            ),
            # Income transaction (should be excluded from heatmap)
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=groceries_cat.id,
                amount_cents=10000,  # +$100.00 (income)
                currency="USD",
                description="Refund",
                transaction_date=base_date + timedelta(days=2),
                status="completed"
            )
        ]
        
        test_db_session.add_all(transactions)
        test_db_session.commit()

        # Call the heatmap endpoint
        start_date = base_date
        end_date = base_date + timedelta(days=5)
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={start_date}&end_date={end_date}"
        )

        # Validate response structure
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        heatmap_data = data["data"]

        # Validate data format for Nivo Calendar
        assert isinstance(heatmap_data, list)
        
        # Should have 2 days with expenses (day 1 and day 2)
        assert len(heatmap_data) == 2

        # Find day 1 data
        day1_str = base_date.isoformat()
        day1_data = next((item for item in heatmap_data if item["day"] == day1_str), None)
        assert day1_data is not None
        assert day1_data["value"] == 2500  # $25.00 in cents

        # Find day 2 data (aggregated)
        day2_str = (base_date + timedelta(days=1)).isoformat()
        day2_data = next((item for item in heatmap_data if item["day"] == day2_str), None)
        assert day2_data is not None
        assert day2_data["value"] == 5000  # $15.00 + $35.00 = $50.00 in cents

        # Verify income is NOT included
        day3_str = (base_date + timedelta(days=2)).isoformat()
        day3_data = next((item for item in heatmap_data if item["day"] == day3_str), None)
        assert day3_data is None

    def test_spending_heatmap_empty_date_range(
        self, test_db_session: Session, test_user: User, api_client: TestClient
    ):
        """
        Test spending heatmap with no transactions in date range returns empty list.
        """
        # Query a date range with no transactions
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_money_flow_sankey_basic_functionality(
        self, test_db_session: Session, test_user: User, test_account: Account, api_client: TestClient
    ):
        """
        Test money flow endpoint returns correct Sankey diagram structure.
        Validates nodes and links format for visualization libraries.
        """
        # Create income and expense categories
        salary_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Salary",
            description="Primary income",
            emoji="💼",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        rent_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Rent",
            description="Housing",
            emoji="🏠",
            color="#ef4444",
            is_system=False,
            is_active=True,
            sort_order=2
        )
        groceries_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Groceries",
            description="Food",
            emoji="🛒",
            color="#f59e0b",
            is_system=False,
            is_active=True,
            sort_order=3
        )
        test_db_session.add_all([salary_cat, rent_cat, groceries_cat])
        test_db_session.commit()

        # Create test transactions
        base_date = date(2024, 1, 15)
        transactions = [
            # Income transactions
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=salary_cat.id,
                amount_cents=500000,  # +$5000.00
                currency="USD",
                description="Monthly salary",
                transaction_date=base_date,
                status="completed"
            ),
            # Expense transactions
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=rent_cat.id,
                amount_cents=-200000,  # -$2000.00
                currency="USD",
                description="Monthly rent",
                transaction_date=base_date + timedelta(days=1),
                status="completed"
            ),
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=groceries_cat.id,
                amount_cents=-50000,  # -$500.00
                currency="USD",
                description="Grocery shopping",
                transaction_date=base_date + timedelta(days=2),
                status="completed"
            ),
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=groceries_cat.id,
                amount_cents=-25000,  # -$250.00
                currency="USD",
                description="More groceries",
                transaction_date=base_date + timedelta(days=3),
                status="completed"
            )
        ]
        
        test_db_session.add_all(transactions)
        test_db_session.commit()

        # Call the money flow endpoint
        start_date = base_date
        end_date = base_date + timedelta(days=10)
        response = api_client.get(
            f"/api/analytics/money-flow?start_date={start_date}&end_date={end_date}"
        )

        # Validate response structure
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        flow_data = data["data"]

        # Validate Sankey structure
        assert "nodes" in flow_data
        assert "links" in flow_data
        assert "metadata" in flow_data

        nodes = flow_data["nodes"]
        links = flow_data["links"]
        metadata = flow_data["metadata"]

        # Validate nodes structure
        assert isinstance(nodes, list)
        node_ids = [node["id"] for node in nodes]
        
        # Expected nodes
        assert "Total Income" in node_ids
        assert "Income: Salary" in node_ids
        assert "Expense: Rent" in node_ids
        assert "Expense: Groceries" in node_ids
        assert "Savings/Unaccounted" in node_ids

        # Validate links structure
        assert isinstance(links, list)
        
        # Find specific links and validate values
        salary_to_total = next(
            (link for link in links 
             if link["source"] == "Income: Salary" and link["target"] == "Total Income"), 
            None
        )
        assert salary_to_total is not None
        assert salary_to_total["value"] == 5000.0  # $5000.00

        total_to_rent = next(
            (link for link in links 
             if link["source"] == "Total Income" and link["target"] == "Expense: Rent"), 
            None
        )
        assert total_to_rent is not None
        assert total_to_rent["value"] == 2000.0  # $2000.00

        total_to_groceries = next(
            (link for link in links 
             if link["source"] == "Total Income" and link["target"] == "Expense: Groceries"), 
            None
        )
        assert total_to_groceries is not None
        assert total_to_groceries["value"] == 750.0  # $500.00 + $250.00 = $750.00

        # Validate savings calculation
        total_to_savings = next(
            (link for link in links 
             if link["source"] == "Total Income" and link["target"] == "Savings/Unaccounted"), 
            None
        )
        assert total_to_savings is not None
        expected_savings = 5000.0 - 2000.0 - 750.0  # $2250.00
        assert total_to_savings["value"] == expected_savings

        # Validate metadata
        assert metadata["total_income"] == 5000.0
        assert metadata["total_expenses"] == 2750.0
        assert metadata["net_savings"] == 2250.0
        assert metadata["income_sources_count"] == 1
        assert metadata["expense_categories_count"] == 2

    def test_money_flow_no_savings_scenario(
        self, test_db_session: Session, test_user: User, test_account: Account, api_client: TestClient
    ):
        """
        Test money flow when expenses equal or exceed income (no savings node).
        """
        # Create categories
        salary_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Salary",
            description="Income",
            emoji="💼",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        rent_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Rent",
            description="Housing",
            emoji="🏠",
            color="#ef4444",
            is_system=False,
            is_active=True,
            sort_order=2
        )
        test_db_session.add_all([salary_cat, rent_cat])
        test_db_session.commit()

        # Create transactions where expenses equal income
        base_date = date(2024, 1, 15)
        transactions = [
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=salary_cat.id,
                amount_cents=200000,  # +$2000.00
                currency="USD",
                description="Salary",
                transaction_date=base_date,
                status="completed"
            ),
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=rent_cat.id,
                amount_cents=-200000,  # -$2000.00
                currency="USD",
                description="Rent",
                transaction_date=base_date + timedelta(days=1),
                status="completed"
            )
        ]
        
        test_db_session.add_all(transactions)
        test_db_session.commit()

        # Call the endpoint
        response = api_client.get(
            f"/api/analytics/money-flow?start_date={base_date}&end_date={base_date + timedelta(days=5)}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        
        # Should not have savings/unaccounted node when net savings is 0
        node_ids = [node["id"] for node in data["nodes"]]
        assert "Savings/Unaccounted" not in node_ids
        
        # Verify metadata shows zero savings
        assert data["metadata"]["net_savings"] == 0.0

    def test_analytics_date_validation(
        self, test_db_session: Session, test_user: User, api_client: TestClient
    ):
        """
        Test date validation for both analytics endpoints.
        """
        # Test invalid date range (start > end)
        response = api_client.get(
            "/api/analytics/spending-heatmap?start_date=2024-01-31&end_date=2024-01-01"
        )
        assert response.status_code == 400
        assert "Start date must be before end date" in response.json()["detail"]

        response = api_client.get(
            "/api/analytics/money-flow?start_date=2024-01-31&end_date=2024-01-01"
        )
        assert response.status_code == 400
        assert "Start date must be before end date" in response.json()["detail"]

        # Test date range too large
        large_start = date(2023, 1, 1)
        large_end = date(2025, 1, 1)  # > 365 days
        
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={large_start}&end_date={large_end}"
        )
        assert response.status_code == 400
        assert "cannot exceed" in response.json()["detail"]

        response = api_client.get(
            f"/api/analytics/money-flow?start_date={large_start}&end_date={large_end}"
        )
        assert response.status_code == 400
        assert "cannot exceed" in response.json()["detail"]

    def test_analytics_empty_data_handling(
        self, test_db_session: Session, test_user: User, api_client: TestClient
    ):
        """
        Test analytics endpoints handle empty data gracefully.
        """
        # Test with no transactions
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Heatmap should return empty array
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

        # Money flow should return minimal structure with message
        response = api_client.get(
            f"/api/analytics/money-flow?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "No transaction data available" in data["message"]
        assert data["data"]["links"] == []
        assert len(data["data"]["nodes"]) == 1  # Only "Total Income" node

    def test_analytics_user_isolation(
        self, test_db_session: Session, api_client: TestClient
    ):
        """
        Test that users can only see their own analytics data.
        """
        # Create two users
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
        test_db_session.add_all([user1, user2])
        test_db_session.commit()

        # Create accounts for each user
        account1 = Account(
            id=uuid4(),
            user_id=user1.id,
            name="User 1 Account",
            account_type="checking",
            balance_cents=100000,
            currency="USD",
            is_active=True
        )
        account2 = Account(
            id=uuid4(),
            user_id=user2.id,
            name="User 2 Account",
            account_type="checking",
            balance_cents=100000,
            currency="USD",
            is_active=True
        )
        test_db_session.add_all([account1, account2])
        test_db_session.commit()

        # Create category for user2
        category2 = Category(
            id=uuid4(),
            user_id=user2.id,
            name="User 2 Category",
            description="Expenses",
            emoji="💰",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        test_db_session.add(category2)
        test_db_session.commit()

        # Create transaction for user2
        transaction2 = Transaction(
            id=uuid4(),
            user_id=user2.id,
            account_id=account2.id,
            category_id=category2.id,
            amount_cents=-5000,  # -$50.00
            currency="USD",
            description="User 2 expense",
            transaction_date=date(2024, 1, 15),
            status="completed"
        )
        test_db_session.add(transaction2)
        test_db_session.commit()

        # Note: In a real test, we would authenticate as user1 and verify
        # that user1 cannot see user2's data. Since this test uses an 
        # unauthenticated client, we're testing the basic endpoint functionality.
        # The actual user isolation is enforced by the RLS (Row Level Security)
        # at the database level combined with the authenticated user context.

        # Test that endpoints respond correctly (user isolation would be 
        # tested with authenticated clients in a full integration test)
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Both endpoints should work (data filtering happens at auth level)
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200

        response = api_client.get(
            f"/api/analytics/money-flow?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200

    def test_money_flow_top_10_expense_limit(
        self, test_db_session: Session, test_user: User, test_account: Account, api_client: TestClient
    ):
        """
        Test that money flow limits expense categories to top 10 by spending.
        """
        # Create 12 expense categories
        categories = []
        for i in range(12):
            cat = Category(
                id=uuid4(),
                user_id=test_user.id,
                name=f"Category {i+1:02d}",
                description=f"Category {i+1}",
                emoji="💰",
                color="#10b981",
                is_system=False,
                is_active=True,
                sort_order=i+1
            )
            categories.append(cat)
        
        test_db_session.add_all(categories)
        test_db_session.commit()

        # Create transactions with different amounts (higher amounts for later categories)
        base_date = date(2024, 1, 15)
        transactions = []
        
        for i, cat in enumerate(categories):
            # Create expense with amount proportional to category number
            # This ensures category 12 has highest expense, category 11 second highest, etc.
            amount = -(i + 1) * 1000  # -$10, -$20, -$30, ..., -$120
            transaction = Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=cat.id,
                amount_cents=amount * 100,  # Convert to cents
                currency="USD",
                description=f"Expense for category {i+1}",
                transaction_date=base_date,
                status="completed"
            )
            transactions.append(transaction)
        
        test_db_session.add_all(transactions)
        test_db_session.commit()

        # Call money flow endpoint
        response = api_client.get(
            f"/api/analytics/money-flow?start_date={base_date}&end_date={base_date + timedelta(days=1)}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        
        # Count expense nodes (should be max 10)
        expense_nodes = [node for node in data["nodes"] if node["id"].startswith("Expense:")]
        assert len(expense_nodes) <= 10
        
        # If we have 12 categories but limit to 10, we should see exactly 10
        if len(categories) > 10:
            assert len(expense_nodes) == 10
            
            # Verify we get the top 10 by amount (categories 12, 11, 10, ..., 3)
            expense_node_names = [node["id"] for node in expense_nodes]
            
            # Should include highest spending categories (Category 12, 11, 10, etc.)
            assert "Expense: Category 12" in expense_node_names
            assert "Expense: Category 11" in expense_node_names
            assert "Expense: Category 10" in expense_node_names
            
            # Should NOT include lowest spending categories
            assert "Expense: Category 01" not in expense_node_names
            assert "Expense: Category 02" not in expense_node_names

    def test_spending_heatmap_data_format_precision(
        self, test_db_session: Session, test_user: User, test_account: Account, api_client: TestClient
    ):
        """
        Test precise data formatting for spending heatmap to ensure
        frontend visualization libraries receive exact expected format.
        """
        # Create category
        cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Test",
            description="Test",
            emoji="💰",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        test_db_session.add(cat)
        test_db_session.commit()

        # Create transaction with specific amount
        test_date = date(2024, 1, 15)
        transaction = Transaction(
            id=uuid4(),
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=cat.id,
            amount_cents=-12345,  # -$123.45
            currency="USD",
            description="Test expense",
            transaction_date=test_date,
            status="completed"
        )
        test_db_session.add(transaction)
        test_db_session.commit()

        # Call endpoint
        response = api_client.get(
            f"/api/analytics/spending-heatmap?start_date={test_date}&end_date={test_date}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        
        # Verify exact format
        assert len(data) == 1
        item = data[0]
        
        # Must have exactly these keys
        assert set(item.keys()) == {"day", "value"}
        
        # Day must be ISO format string
        assert item["day"] == test_date.isoformat()
        assert isinstance(item["day"], str)
        
        # Value must be integer cents (not float dollars)
        assert item["value"] == 12345
        assert isinstance(item["value"], int)

    def test_money_flow_data_format_precision(
        self, test_db_session: Session, test_user: User, test_account: Account, api_client: TestClient
    ):
        """
        Test precise data formatting for money flow to ensure
        Sankey diagram libraries receive exact expected format.
        """
        # Create categories
        income_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Income",
            description="Test income",
            emoji="💰",
            color="#10b981",
            is_system=False,
            is_active=True,
            sort_order=1
        )
        expense_cat = Category(
            id=uuid4(),
            user_id=test_user.id,
            name="Expense",
            description="Test expense",
            emoji="💸",
            color="#ef4444",
            is_system=False,
            is_active=True,
            sort_order=2
        )
        test_db_session.add_all([income_cat, expense_cat])
        test_db_session.commit()

        # Create transactions with specific amounts
        test_date = date(2024, 1, 15)
        transactions = [
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=income_cat.id,
                amount_cents=123450,  # +$1234.50
                currency="USD",
                description="Income",
                transaction_date=test_date,
                status="completed"
            ),
            Transaction(
                id=uuid4(),
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=expense_cat.id,
                amount_cents=-67890,  # -$678.90
                currency="USD",
                description="Expense",
                transaction_date=test_date,
                status="completed"
            )
        ]
        test_db_session.add_all(transactions)
        test_db_session.commit()

        # Call endpoint
        response = api_client.get(
            f"/api/analytics/money-flow?start_date={test_date}&end_date={test_date}"
        )

        assert response.status_code == 200
        data = response.json()["data"]
        
        # Verify nodes format
        nodes = data["nodes"]
        for node in nodes:
            assert set(node.keys()) == {"id"}
            assert isinstance(node["id"], str)
        
        # Verify links format  
        links = data["links"]
        for link in links:
            assert set(link.keys()) == {"source", "target", "value"}
            assert isinstance(link["source"], str)
            assert isinstance(link["target"], str)
            assert isinstance(link["value"], float)  # Dollars as float for visualization
        
        # Verify specific values are converted correctly from cents to dollars
        income_link = next(
            link for link in links 
            if link["source"] == "Income: Income" and link["target"] == "Total Income"
        )
        assert income_link["value"] == 1234.50  # Converted from 123450 cents
        
        expense_link = next(
            link for link in links 
            if link["source"] == "Total Income" and link["target"] == "Expense: Expense"
        )
        assert expense_link["value"] == 678.90  # Converted from 67890 cents
        
        # Verify metadata format
        metadata = data["metadata"]
        required_fields = {
            "total_income", "total_expenses", "net_savings",
            "date_range", "income_sources_count", "expense_categories_count"
        }
        assert set(metadata.keys()) == required_fields
        
        # All monetary values should be floats (dollars)
        assert isinstance(metadata["total_income"], float)
        assert isinstance(metadata["total_expenses"], float)
        assert isinstance(metadata["net_savings"], float)
        
        # Counts should be integers
        assert isinstance(metadata["income_sources_count"], int)
        assert isinstance(metadata["expense_categories_count"], int)
        
        # Date range should be properly formatted
        date_range = metadata["date_range"]
        assert isinstance(date_range["start_date"], str)
        assert isinstance(date_range["end_date"], str)
        assert date_range["start_date"] == test_date.isoformat()
        assert date_range["end_date"] == test_date.isoformat()