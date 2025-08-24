# Standard library imports
import logging
import uuid

# Third-party imports
from sqlalchemy.orm import Session

# Local imports
from app.models import Category, User
from app.database import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)

# Constants
TEST_USER_EMAIL = "test@example.com"
TEST_USER_DISPLAY_NAME = "Test User"
TEST_USER_LOCALE = "en-US"
TEST_USER_TIMEZONE = "America/New_York"
TEST_USER_CURRENCY = "USD"
DEFAULT_SUBCATEGORY_COLOR = "#CCCCCC"

# Default system categories
DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "emoji": "🍽️", "color": "#FF6B6B"},
    {"name": "Transportation", "emoji": "🚗", "color": "#4ECDC4"},
    {"name": "Shopping", "emoji": "🛍️", "color": "#45B7D1"},
    {"name": "Entertainment", "emoji": "🎬", "color": "#96CEB4"},
    {"name": "Bills & Utilities", "emoji": "💡", "color": "#FFEAA7"},
    {"name": "Health & Fitness", "emoji": "🏥", "color": "#DDA0DD"},
    {"name": "Travel", "emoji": "✈️", "color": "#98D8C8"},
    {"name": "Education", "emoji": "📚", "color": "#F7DC6F"},
    {"name": "Income", "emoji": "💰", "color": "#82E0AA"},
    {"name": "Other", "emoji": "📋", "color": "#AED6F1"},
]

# Subcategories
SUBCATEGORIES = {
    "Food & Dining": [
        {"name": "Restaurants", "emoji": "🍽️"},
        {"name": "Fast Food", "emoji": "🍔"},
        {"name": "Groceries", "emoji": "🛒"},
        {"name": "Coffee & Tea", "emoji": "☕"},
        {"name": "Alcohol & Bars", "emoji": "🍺"},
    ],
    "Transportation": [
        {"name": "Gas & Fuel", "emoji": "⛽"},
        {"name": "Public Transportation", "emoji": "🚌"},
        {"name": "Taxi & Rideshare", "emoji": "🚕"},
        {"name": "Parking", "emoji": "🅿️"},
        {"name": "Car Maintenance", "emoji": "🔧"},
    ],
    "Shopping": [
        {"name": "Clothing", "emoji": "👕"},
        {"name": "Electronics", "emoji": "📱"},
        {"name": "Home & Garden", "emoji": "🏠"},
        {"name": "Personal Care", "emoji": "💄"},
        {"name": "Gifts & Donations", "emoji": "🎁"},
    ],
    "Bills & Utilities": [
        {"name": "Rent & Mortgage", "emoji": "🏠"},
        {"name": "Electricity", "emoji": "💡"},
        {"name": "Water", "emoji": "💧"},
        {"name": "Internet & Phone", "emoji": "📞"},
        {"name": "Insurance", "emoji": "🛡️"},
    ]
}

def create_system_categories(db: Session):
    """Create default system categories"""
    logger.info("Creating system categories...")
    
    # Create main categories
    category_map = {}
    for cat_data in DEFAULT_CATEGORIES:
        category = Category(
            user_id=None,  # System category
            name=cat_data["name"],
            emoji=cat_data["emoji"],
            color=cat_data["color"],
            is_system=True
        )
        db.add(category)
        db.flush()  # Get the ID
        category_map[cat_data["name"]] = category.id
    
    # Create subcategories
    for parent_name, subcats in SUBCATEGORIES.items():
        parent_id = category_map.get(parent_name)
        if parent_id:
            for subcat_data in subcats:
                subcategory = Category(
                    user_id=None,
                    name=subcat_data["name"],
                    emoji=subcat_data["emoji"],
                    color=DEFAULT_SUBCATEGORY_COLOR,
                    parent_id=parent_id,
                    is_system=True
                )
                db.add(subcategory)
    
    db.commit()
    logger.info(f"Created {len(DEFAULT_CATEGORIES)} main categories and {sum(len(subs) for subs in SUBCATEGORIES.values())} subcategories")

def create_test_user(db: Session):
    """Create a test user for development"""
    logger.info("Creating test user...")
    
    test_user = User(
        email=TEST_USER_EMAIL,
        display_name=TEST_USER_DISPLAY_NAME,
        locale=TEST_USER_LOCALE,
        timezone=TEST_USER_TIMEZONE,
        currency=TEST_USER_CURRENCY
    )
    db.add(test_user)
    db.commit()
    logger.info(f"Created test user: {test_user.email}")
    return test_user

def seed_database():
    """Main seeding function"""
    db = SessionLocal()
    try:
        logger.info("Starting database seeding...")
        
        # Check if categories already exist
        existing_categories = db.query(Category).filter(Category.is_system == True).count()
        if existing_categories > 0:
            logger.info(f"Found {existing_categories} existing system categories. Skipping category creation.")
        else:
            create_system_categories(db)
        
        # Check if test user exists
        existing_user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
        if existing_user:
            logger.info("Test user already exists. Skipping user creation.")
        else:
            create_test_user(db)
        
        logger.info("Database seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    seed_database()