#!/usr/bin/env python3
"""
Initialize database tables
"""
import sys
from pathlib import Path

# Add the parent directory to Python path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine
from app.models import Base

def init_database():
    """Create all database tables"""
    print("Creating database tables...")
    
    # Import all models to ensure they're registered with Base
    from app.models import (
        User, UserPreferences, Category, Account, Transaction, 
        Budget, Goal, Insight, MLModelPerformance
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    
    # List created tables
    print("\nCreated tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

if __name__ == "__main__":
    init_database()