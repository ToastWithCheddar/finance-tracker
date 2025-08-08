import asyncio
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import Base
from app.seed_data import seed_database
import logging

logging.basicConfig(level=logging.INFO)
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
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, transaction_date DESC);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount_cents);",
                "CREATE INDEX IF NOT EXISTS idx_budgets_user_active ON budgets(user_id) WHERE is_active = TRUE;",
                "CREATE INDEX IF NOT EXISTS idx_insights_user_unread ON insights(user_id) WHERE is_read = FALSE;",
                "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);",
                "CREATE INDEX IF NOT EXISTS idx_categories_system ON categories(is_system);",
                "CREATE INDEX IF NOT EXISTS idx_transactions_description_fts ON transactions USING GIN(to_tsvector('english', description));",
                "CREATE INDEX IF NOT EXISTS idx_transactions_merchant_trgm ON transactions USING GIN(merchant gin_trgm_ops);"
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
            triggers = [
                # Updated_at triggers for all tables
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
                # Budget alert trigger
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

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py [create|drop|reset|seed|indexes|triggers|full]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        DatabaseManager.create_tables()
    elif command == "drop":
        DatabaseManager.drop_tables()
    elif command == "reset":
        DatabaseManager.reset_database()
    elif command == "seed":
        DatabaseManager.seed_data()
    elif command == "indexes":
        DatabaseManager.create_indexes()
    elif command == "triggers":
        DatabaseManager.setup_triggers()
    elif command == "full":
        DatabaseManager.full_setup()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)