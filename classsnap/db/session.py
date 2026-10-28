"""
Database connection and session management for ClassSnap.
"""

from typing import Generator
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from classsnap.config import get_settings
from classsnap.db.base import Base
from classsnap.logger import get_logger

logger = get_logger("db")

settings = get_settings()

# Configure engine with SQLite-specific optimizations
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine: Engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine: Engine = engine) -> None:
    """Creates database tables based on registered models."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=target_engine)
    if "attendance_sessions" in inspect(target_engine).get_table_names():
        columns = {
            column["name"]
            for column in inspect(target_engine).get_columns("attendance_sessions")
        }
        if "class_at" not in columns:
            with target_engine.begin() as connection:
                connection.execute(text("ALTER TABLE attendance_sessions ADD COLUMN class_at DATETIME"))
    logger.info("Database tables successfully initialized.")


def check_db_health(db: Session) -> bool:
    """Verifies that the database connection is alive."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
