from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging
from contextlib import contextmanager
from typing import Generator

from app.config import settings

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = settings.DATABASE_URL

# Create engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
    connect_args={
        "application_name": "finance-tracker",
        "client_encoding": "utf8",
    } if "postgresql" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Database session dependency
def get_db() -> Generator[Session, None, None]:
    """Get database session as a generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Context manager for database sessions
@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Database health check
def check_database_health() -> bool:
    """Check if database is healthy"""
    try:
        with get_db_session() as db:
            # In SQLAlchemy 2.x all ad‑hoc SQL strings must be wrapped in text()
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

# Function to create database if it does not exist
def create_database():
    """Create database if it does not exist"""
    try:
        from sqlalchemy_utils import database_exists, create_database as create_db
        if not database_exists(engine.url):
            create_db(engine.url)
            logger.info("Database created.")
        else:
            logger.info("Database already exists.")
    except ImportError:
        logger.warning("sqlalchemy_utils not available, skipping database creation check")
    except Exception as e:
        logger.error(f"Database creation check failed: {e}")
        # Don't raise - let the application continue and fail later if DB doesn't exist

# SQLAlchemy events
# Check what exactly is that? 
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for foreign key constraints"""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries in debug mode"""
    if settings.DEBUG:
        logger.debug(f"SQL Query: {statement}")
        logger.debug(f"Parameters: {parameters}")