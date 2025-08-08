"""
Mock data service for UI development without database dependencies
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import random
import uuid

logger = logging.getLogger(__name__)

class MockDataService:
    """Service providing mock data for UI development"""
    
    def __init__(self):
        self.mock_users = self._generate_mock_users()
        self.mock_categories = self._generate_mock_categories()
        self.mock_accounts = self._generate_mock_accounts()
        self.mock_transactions = self._generate_mock_transactions()
        self.mock_budgets = self._generate_mock_budgets()
        self.mock_goals = self._generate_mock_goals()
    
    def _generate_mock_users(self) -> List[Dict[str, Any]]:
        """Generate mock user data"""
        return [
            {
                "id": "user-1",
                "email": "demo@financetracker.dev",
                "username": "demo_user",
                "first_name": "Demo",
                "last_name": "User",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "preferences": {
                    "currency": "USD",
                    "date_format": "MM/DD/YYYY",
                    "theme": "light"
                }
            }
        ]
    
    def _generate_mock_categories(self) -> List[Dict[str, Any]]:
        """Generate mock category data"""
        categories = [
            {"name": "Food & Dining", "icon": "🍔", "color": "#FF6B6B", "type": "expense"},
            {"name": "Transportation", "icon": "🚗", "color": "#4ECDC4", "type": "expense"},
            {"name": "Shopping", "icon": "🛍️", "color": "#45B7D1", "type": "expense"},
            {"name": "Entertainment", "icon": "🎬", "color": "#96CEB4", "type": "expense"},
            {"name": "Bills & Utilities", "icon": "⚡", "color": "#FFEAA7", "type": "expense"},
            {"name": "Healthcare", "icon": "🏥", "color": "#DDA0DD", "type": "expense"},
            {"name": "Salary", "icon": "💰", "color": "#00B894", "type": "income"},
            {"name": "Freelance", "icon": "💻", "color": "#00CEC9", "type": "income"},
            {"name": "Investments", "icon": "📈", "color": "#6C5CE7", "type": "income"},
        ]
        
        return [
            {
                "id": f"cat-{i+1}",
                "user_id": "user-1",
                "name": cat["name"],
                "icon": cat["icon"],
                "color": cat["color"],
                "category_type": cat["type"],
                "is_default": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            for i, cat in enumerate(categories)
        ]
    
    def _generate_mock_accounts(self) -> List[Dict[str, Any]]:
        """Generate mock account data"""
        accounts = [
            {
                "name": "Chase Checking",
                "type": "checking",
                "balance": 2450.75,
                "currency": "USD",
                "institution": "Chase Bank"
            },
            {
                "name": "Savings Account",
                "type": "savings", 
                "balance": 8925.50,
                "currency": "USD",
                "institution": "Chase Bank"
            },
            {
                "name": "Credit Card",
                "type": "credit_card",
                "balance": -1250.30,
                "currency": "USD",
                "institution": "Capital One"
            }
        ]
        
        return [
            {
                "id": f"acc-{i+1}",
                "user_id": "user-1",
                "name": acc["name"],
                "account_type": acc["type"],
                "balance_cents": int(acc["balance"] * 100),
                "currency": acc["currency"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "account_metadata": {
                    "institution": acc["institution"],
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            }
            for i, acc in enumerate(accounts)
        ]
    
    def _generate_mock_transactions(self) -> List[Dict[str, Any]]:
        """Generate mock transaction data"""
        transactions = []
        categories = self.mock_categories
        accounts = self.mock_accounts
        
        # Generate transactions for the last 30 days
        for i in range(50):
            days_ago = random.randint(0, 30)
            transaction_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            
            # Pick random category and account
            category = random.choice(categories)
            account = random.choice(accounts)
            
            # Generate realistic amounts based on category
            if category["category_type"] == "income":
                amount = random.uniform(500, 5000)
                is_income = True
            else:
                amount = random.uniform(5, 500)
                is_income = False
            
            # Sample merchant names
            merchants = {
                "Food & Dining": ["Starbucks", "McDonald's", "Local Restaurant", "Pizza Palace"],
                "Transportation": ["Uber", "Gas Station", "Metro Card", "Parking Meter"],
                "Shopping": ["Amazon", "Target", "Walmart", "Best Buy"],
                "Entertainment": ["Netflix", "Spotify", "Movie Theater", "Concert Hall"],
                "Bills & Utilities": ["Electric Company", "Water Dept", "Internet Provider"],
                "Healthcare": ["Dr. Smith", "Pharmacy", "Dental Care"],
                "Salary": ["ACME Corp", "Employer Inc"],
                "Freelance": ["Client ABC", "Project XYZ"],
                "Investments": ["Dividend", "Stock Sale", "Bond Interest"]
            }
            
            merchant = random.choice(merchants.get(category["name"], ["Generic Merchant"]))
            
            transaction = {
                "id": f"txn-{i+1}",
                "user_id": "user-1",
                "account_id": account["id"],
                "category_id": category["id"],
                "amount_cents": int(amount * 100),
                "description": merchant,
                "transaction_date": transaction_date.isoformat(),
                "is_income": is_income,
                "is_recurring": random.choice([True, False]) if i % 10 == 0 else False,
                "created_at": transaction_date.isoformat(),
                "transaction_metadata": {
                    "merchant": merchant,
                    "location": "Demo City, ST",
                    "confidence": random.uniform(0.8, 1.0)
                }
            }
            
            transactions.append(transaction)
        
        return sorted(transactions, key=lambda x: x["transaction_date"], reverse=True)
    
    def _generate_mock_budgets(self) -> List[Dict[str, Any]]:
        """Generate mock budget data"""
        expense_categories = [cat for cat in self.mock_categories if cat["category_type"] == "expense"]
        budgets = []
        
        for i, category in enumerate(expense_categories[:5]):  # Only create budgets for first 5 categories
            budget_amount = random.uniform(200, 800)
            spent_amount = random.uniform(0, budget_amount * 1.2)  # Sometimes over budget
            
            budget = {
                "id": f"budget-{i+1}",
                "user_id": "user-1",
                "category_id": category["id"],
                "amount_cents": int(budget_amount * 100),
                "period": "monthly",
                "start_date": datetime.now(timezone.utc).replace(day=1).isoformat(),
                "end_date": (datetime.now(timezone.utc).replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "spent_amount_cents": int(spent_amount * 100),
                "remaining_amount_cents": int((budget_amount - spent_amount) * 100)
            }
            
            budgets.append(budget)
        
        return budgets
    
    def _generate_mock_goals(self) -> List[Dict[str, Any]]:
        """Generate mock financial goals"""
        goals = [
            {
                "name": "Emergency Fund",
                "target_amount": 10000.00,
                "current_amount": 6500.00,
                "target_date": "2024-12-31",
                "category": "savings"
            },
            {
                "name": "Vacation to Europe",
                "target_amount": 5000.00,
                "current_amount": 2300.00,
                "target_date": "2024-08-15",
                "category": "travel"
            },
            {
                "name": "New Car Down Payment",
                "target_amount": 8000.00,
                "current_amount": 4200.00,
                "target_date": "2024-10-01",
                "category": "transport"
            }
        ]
        
        return [
            {
                "id": f"goal-{i+1}",
                "user_id": "user-1",
                "name": goal["name"],
                "target_amount_cents": int(goal["target_amount"] * 100),
                "current_amount_cents": int(goal["current_amount"] * 100),
                "target_date": goal["target_date"],
                "category": goal["category"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "progress_percentage": (goal["current_amount"] / goal["target_amount"]) * 100
            }
            for i, goal in enumerate(goals)
        ]
    
    def get_mock_user(self, user_id: str = "user-1") -> Dict[str, Any]:
        """Get mock user data"""
        return next((user for user in self.mock_users if user["id"] == user_id), self.mock_users[0])
    
    def get_mock_accounts(self, user_id: str = "user-1") -> List[Dict[str, Any]]:
        """Get mock account data"""
        return [acc for acc in self.mock_accounts if acc["user_id"] == user_id]
    
    def get_mock_transactions(self, user_id: str = "user-1", limit: int = 50) -> List[Dict[str, Any]]:
        """Get mock transaction data"""
        transactions = [txn for txn in self.mock_transactions if txn["user_id"] == user_id]
        return transactions[:limit]
    
    def get_mock_categories(self, user_id: str = "user-1") -> List[Dict[str, Any]]:
        """Get mock category data"""
        return [cat for cat in self.mock_categories if cat["user_id"] == user_id]
    
    def get_mock_budgets(self, user_id: str = "user-1") -> List[Dict[str, Any]]:
        """Get mock budget data"""
        return [budget for budget in self.mock_budgets if budget["user_id"] == user_id]
    
    def get_mock_goals(self, user_id: str = "user-1") -> List[Dict[str, Any]]:
        """Get mock goal data"""
        return [goal for goal in self.mock_goals if goal["user_id"] == user_id]
    
    def get_dashboard_summary(self, user_id: str = "user-1") -> Dict[str, Any]:
        """Get mock dashboard summary data"""
        accounts = self.get_mock_accounts(user_id)
        transactions = self.get_mock_transactions(user_id, 30)
        budgets = self.get_mock_budgets(user_id)
        
        total_balance = sum(acc["balance_cents"] for acc in accounts) / 100
        
        # Calculate monthly spending
        current_month_start = datetime.now(timezone.utc).replace(day=1)
        monthly_spending = sum(
            txn["amount_cents"] for txn in transactions 
            if not txn["is_income"] and 
            datetime.fromisoformat(txn["transaction_date"].replace("Z", "")) >= current_month_start
        ) / 100
        
        # Calculate monthly income
        monthly_income = sum(
            txn["amount_cents"] for txn in transactions 
            if txn["is_income"] and 
            datetime.fromisoformat(txn["transaction_date"].replace("Z", "")) >= current_month_start
        ) / 100
        
        return {
            "total_balance": total_balance,
            "monthly_spending": monthly_spending,
            "monthly_income": monthly_income,
            "net_worth": total_balance,
            "budget_utilization": sum(budget["spent_amount_cents"] for budget in budgets) / 100,
            "active_budgets": len(budgets),
            "recent_transactions_count": len(transactions[:10]),
            "accounts_count": len(accounts)
        }

# Create global mock service instance
mock_data_service = MockDataService()