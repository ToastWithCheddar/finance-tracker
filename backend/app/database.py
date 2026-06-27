# Standard library imports
import logging
import os
from contextlib import contextmanager
from typing import Generator

# Third-party imports
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Local imports
from app.config import settings

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = settings.DATABASE_URL

# BE-LOG-003: SQL echo is dev-only AND opt-in via LOG_SQL_PARAMS.
# Default OFF in non-development environments to avoid PII leaks.
_ENV_IS_DEV = os.getenv("ENVIRONMENT", "development").lower() == "development"
_LOG_SQL_PARAMS = os.getenv("LOG_SQL_PARAMS", "").lower() in {"1", "true", "yes", "on"}
_ECHO_SQL = bool(_ENV_IS_DEV and _LOG_SQL_PARAMS)


class _TruncatingFilter(logging.Filter):
    """Truncate any SQLAlchemy log message that exceeds the limit."""

    def __init__(self, max_chars: int = 200) -> None:
        super().__init__()
        self.max_chars = max_chars

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if len(msg) > self.max_chars:
            record.msg = msg[: self.max_chars] + "...[truncated]"
            record.args = ()
        return True


# Apply truncation filter to SQLAlchemy loggers.
for _name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine"):
    logging.getLogger(_name).addFilter(_TruncatingFilter(200))

# Create engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=_ECHO_SQL,
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

# Context manager for database sessions (for "with" statement)
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
# Just for the quick tests 
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragma for foreign key constraints"""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries in dev when LOG_SQL_PARAMS is opt-in. Truncated to 200 chars."""
    if _ENV_IS_DEV and _LOG_SQL_PARAMS:
        stmt = (statement or "")[:200]
        params_repr = repr(parameters)
        if len(params_repr) > 200:
            params_repr = params_repr[:200] + "...[truncated]"
        logger.debug(f"SQL Query: {stmt}")
        logger.debug(f"Parameters: {params_repr}")