from sqlalchemy.orm import Session
from app.database import get_db_session
from app.config import settings
import logging

# Import models individually to avoid conflicts
from app.models.category import Category
from app.models.user import User

logger = logging.getLogger(__name__)

# Default system categories
DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "emoji": "🍽️", "color": "#FF6B6B", "description": "Restaurants, groceries, and dining"},
    {"name": "Transportation", "emoji": "🚗", "color": "#4ECDC4", "description": "Gas, public transport, rideshares"},
    {"name": "Shopping", "emoji": "🛍️", "color": "#45B7D1", "description": "Clothing, electronics, general shopping"},
    {"name": "Entertainment", "emoji": "🎬", "color": "#96CEB4", "description": "Movies, games, subscriptions"},
    {"name": "Bills & Utilities", "emoji": "💡", "color": "#FFEAA7", "description": "Rent, utilities, insurance"},
    {"name": "Health & Fitness", "emoji": "🏥", "color": "#DDA0DD", "description": "Medical, gym, wellness"},
    {"name": "Travel", "emoji": "✈️", "color": "#98D8C8", "description": "Flights, hotels, vacation"},
    {"name": "Education", "emoji": "📚", "color": "#F7DC6F", "description": "Books, courses, training"},
    {"name": "Income", "emoji": "💰", "color": "#82E0AA", "description": "Salary, bonuses, investments"},
    {"name": "Savings", "emoji": "🏦", "color": "#85C1E9", "description": "Emergency fund, retirement"},
    {"name": "Debt Payments", "emoji": "💳", "color": "#F1948A", "description": "Credit cards, loans"},
    {"name": "Gifts & Donations", "emoji": "🎁", "color": "#D7BDE2", "description": "Gifts, charity, donations"},
    {"name": "Personal Care", "emoji": "💄", "color": "#F8C471", "description": "Beauty, grooming, spa"},
    {"name": "Pet Care", "emoji": "🐕", "color": "#A9DFBF", "description": "Pet food, vet, grooming"},
    {"name": "Home & Garden", "emoji": "🏠", "color": "#AED6F1", "description": "Furniture, repairs, gardening"},
    {"name": "Other", "emoji": "📋", "color": "#D5D8DC", "description": "Miscellaneous expenses"},
]

# Subcategories for main categories
SUBCATEGORIES = {
    "Food & Dining": [
        {"name": "Restaurants", "emoji": "🍽️", "color": "#FF6B6B"},
        {"name": "Fast Food", "emoji": "🍔", "color": "#FF6B6B"},
        {"name": "Groceries", "emoji": "🛒", "color": "#FF6B6B"},
        {"name": "Coffee & Tea", "emoji": "☕", "color": "#FF6B6B"},
        {"name": "Alcohol & Bars", "emoji": "🍺", "color": "#FF6B6B"},
        {"name": "Delivery", "emoji": "🚚", "color": "#FF6B6B"},
    ],
    "Transportation": [
        {"name": "Gas & Fuel", "emoji": "⛽", "color": "#4ECDC4"},
        {"name": "Public Transportation", "emoji": "🚌", "color": "#4ECDC4"},
        {"name": "Taxi & Rideshare", "emoji": "🚕", "color": "#4ECDC4"},
        {"name": "Parking", "emoji": "🅿️", "color": "#4ECDC4"},
        {"name": "Car Maintenance", "emoji": "🔧", "color": "#4ECDC4"},
        {"name": "Car Insurance", "emoji": "🚗", "color": "#4ECDC4"},
    ],
    "Shopping": [
        {"name": "Clothing", "emoji": "👕", "color": "#45B7D1"},
        {"name": "Electronics", "emoji": "📱", "color": "#45B7D1"},
        {"name": "Books", "emoji": "📚", "color": "#45B7D1"},
        {"name": "Hobbies", "emoji": "🎨", "color": "#45B7D1"},
        {"name": "Online Shopping", "emoji": "🛒", "color": "#45B7D1"},
    ],
    "Bills & Utilities": [
        {"name": "Rent", "emoji": "🏠", "color": "#FFEAA7"},
        {"name": "Mortgage", "emoji": "🏡", "color": "#FFEAA7"},
        {"name": "Electricity", "emoji": "💡", "color": "#FFEAA7"},
        {"name": "Water", "emoji": "💧", "color": "#FFEAA7"},
        {"name": "Internet", "emoji": "📶", "color": "#FFEAA7"},
        {"name": "Phone", "emoji": "📞", "color": "#FFEAA7"},
        {"name": "Insurance", "emoji": "🛡️", "color": "#FFEAA7"},
    ],
    "Income": [
        {"name": "Salary", "emoji": "💼", "color": "#82E0AA"},
        {"name": "Freelance", "emoji": "💻", "color": "#82E0AA"},
        {"name": "Business", "emoji": "🏢", "color": "#82E0AA"},
        {"name": "Investment", "emoji": "📈", "color": "#82E0AA"},
        {"name": "Interest", "emoji": "🏦", "color": "#82E0AA"},
        {"name": "Bonus", "emoji": "🎉", "color": "#82E0AA"},
        {"name": "Refund", "emoji": "🔄", "color": "#82E0AA"},
    ],
}

def seed_default_categories():
    """Create default system categories"""
    try:
        with get_db_session() as db:
            # Check if categories already exist
            existing_categories = db.query(Category).filter(Category.is_system == True).count()
            if existing_categories > 0:
                logger.info(f"Found {existing_categories} existing system categories. Skipping creation.")
                return
            
            logger.info("Creating default system categories...")
            
            # Create main categories
            category_map = {}
            for cat_data in DEFAULT_CATEGORIES:
                category = Category(
                    user_id=None,  # System category
                    name=cat_data["name"],
                    description=cat_data["description"],
                    emoji=cat_data["emoji"],
                    color=cat_data["color"],
                    is_system=True,
                    is_active=True,
                    sort_order=len(category_map)
                )
                db.add(category)
                db.flush()  # Get the ID

                category_map[cat_data["name"]] = category.id
                logger.info(f"Created category: {cat_data['name']}")
            
            # Create subcategories
            subcategory_count = 0
            for parent_name, subcats in SUBCATEGORIES.items():
                parent_id = category_map.get(parent_name)
                if parent_id:
                    for i, subcat_data in enumerate(subcats):
                        subcategory = Category(
                            user_id=None,
                            name=subcat_data["name"],
                            emoji=subcat_data["emoji"],
                            color=subcat_data["color"],
                            parent_id=parent_id,
                            is_system=True,
                            is_active=True,
                            sort_order=i
                        )
                        db.add(subcategory)
                        subcategory_count += 1
            
            db.commit()
            logger.info(f"✅ Created {len(DEFAULT_CATEGORIES)} main categories and {subcategory_count} subcategories")
            
    except Exception as e:
        logger.error(f"❌ Error creating default categories: {e}")
        raise

def create_test_user():
    """Create a test user for development"""
    if settings.ENVIRONMENT != "development":
        return
    
    try:
        with get_db_session() as db:
            # Check if test user already exists
            existing_user = db.query(User).filter(User.email == "test@example.com").first()
            if existing_user:
                logger.info("Test user already exists. Skipping creation.")
                return
            
            logger.info("Creating test user...")
            
            test_user = User(
                email="test@example.com",
                display_name="Test User",
                first_name="Test",
                last_name="User",
                locale="en-US",
                timezone="America/New_York",
                currency="USD",
                is_active=True,
                is_verified=True
            )
            db.add(test_user)
            db.commit()
            logger.info(f"✅ Created test user: {test_user.email}")
            
    except Exception as e:
        logger.error(f"❌ Error creating test user: {e}")

def seed_all_data():
    """Seed all default data"""
    logger.info("🌱 Starting data seeding...")
    
    try:
        seed_default_categories()
        create_test_user()
        logger.info("🎉 Data seeding completed successfully!")
    except Exception as e:
        logger.error(f"❌ Data seeding failed: {e}")
        raise

if __name__ == "__main__":
    seed_all_data()