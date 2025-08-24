# Standard library imports
import asyncio
import logging
import sys

# Third-party imports
from sqlalchemy import text

# Local imports
from app.database import engine, SessionLocal
from app.models import Base
from app.seed_data import seed_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    @staticmethod
    def create_tables():
        """Create all database tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully")
    
    @staticmethod
    def drop_tables():
        """Drop all database tables"""
        logger.info("Dropping database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Tables dropped successfully")
    
    @staticmethod
    def reset_database():
        """Reset database (drop and recreate tables)"""
        DatabaseManager.drop_tables()
        DatabaseManager.create_tables()
        logger.info("Database reset completed")
    
    @staticmethod
    def seed_data():
        """Seed database with initial data"""
        logger.info("Seeding database...")
        seed_database()
        logger.info("Database seeded successfully")
    
    @staticmethod
    def create_indexes():
        """Create additional database indexes"""
        logger.info("Creating additional indexes...")
        db = SessionLocal()
        try:
            # Database indexes for performance optimization
            indexes = [
                # Transaction indexes
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, transaction_date DESC);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount_cents);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_description_fts ON transactions USING GIN(to_tsvector('english', description));",
                
                # Budget and insights indexes
                "CREATE INDEX IF NOT EXISTS idx_budgets_user_active ON budgets(user_id) WHERE is_active = TRUE;",
                "CREATE INDEX IF NOT EXISTS idx_insights_user_unread ON insights(user_id) WHERE is_read = FALSE;",
                
                # Category indexes
                "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);",
                "CREATE INDEX IF NOT EXISTS idx_categories_system ON categories(is_system);",
            ]
            
            for index_sql in indexes:
                db.execute(text(index_sql))
            
            db.commit()
            logger.info("Indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def setup_triggers():
        """Set up database triggers"""
        logger.info("Setting up database triggers...")
        db = SessionLocal()
        try:
            # Database triggers for automated functionality
            triggers = [
                # Automatic timestamp updates
                """
                CREATE TRIGGER update_users_updated_at 
                BEFORE UPDATE ON users 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                """,
                """
                CREATE TRIGGER update_transactions_updated_at 
                BEFORE UPDATE ON transactions 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                """,
                # Budget monitoring
                """
                CREATE TRIGGER budget_alert_trigger
                AFTER INSERT ON transactions
                FOR EACH ROW EXECUTE FUNCTION notify_budget_alert();
                """
            ]
            
            for trigger_sql in triggers:
                try:
                    db.execute(text(trigger_sql))
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Error creating trigger: {e}")
            
            db.commit()
            logger.info("Triggers set up successfully")
        except Exception as e:
            logger.error(f"Error setting up triggers: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def full_setup():
        """Complete database setup"""
        logger.info("Starting full database setup...")
        DatabaseManager.create_tables()
        DatabaseManager.create_indexes()
        DatabaseManager.setup_triggers()
        DatabaseManager.seed_data()
        logger.info("Full database setup completed")

def main():
    """Command line interface for database management"""
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py [create|drop|reset|seed|indexes|triggers|full]")
        print("\nCommands:")
        print("  create   - Create database tables")
        print("  drop     - Drop all database tables")
        print("  reset    - Drop and recreate tables")
        print("  seed     - Seed database with initial data")
        print("  indexes  - Create performance indexes")
        print("  triggers - Set up database triggers")
        print("  full     - Complete database setup (recommended)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    command_map = {
        "create": DatabaseManager.create_tables,
        "drop": DatabaseManager.drop_tables,
        "reset": DatabaseManager.reset_database,
        "seed": DatabaseManager.seed_data,
        "indexes": DatabaseManager.create_indexes,
        "triggers": DatabaseManager.setup_triggers,
        "full": DatabaseManager.full_setup,
    }
    
    if command in command_map:
        try:
            command_map[command]()
        except Exception as e:
            logger.error(f"Command '{command}' failed: {e}")
            sys.exit(1)
    else:
        logger.error(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()