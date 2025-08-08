from sqlalchemy.orm import Session
from app.models import Category, User
from app.database import SessionLocal
import uuid

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
    print("Creating system categories...")
    
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
                    color="#CCCCCC",  # Default color for subcategories
                    parent_id=parent_id,
                    is_system=True
                )
                db.add(subcategory)
    
    db.commit()
    print(f"Created {len(DEFAULT_CATEGORIES)} main categories and {sum(len(subs) for subs in SUBCATEGORIES.values())} subcategories")

def create_test_user(db: Session):
    """Create a test user for development"""
    print("Creating test user...")
    
    test_user = User(
        email="test@example.com",
        display_name="Test User",
        locale="en-US",
        timezone="America/New_York",
        currency="USD"
    )
    db.add(test_user)
    db.commit()
    print(f"Created test user: {test_user.email}")
    return test_user

def seed_database():
    """Main seeding function"""
    db = SessionLocal()
    try:
        print("Starting database seeding...")
        
        # Check if categories already exist
        existing_categories = db.query(Category).filter(Category.is_system == True).count()
        if existing_categories > 0:
            print(f"Found {existing_categories} existing system categories. Skipping category creation.")
        else:
            create_system_categories(db)
        
        # Check if test user exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            print("Test user already exists. Skipping user creation.")
        else:
            create_test_user(db)
        
        print("Database seeding completed successfully!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()