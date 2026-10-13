import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 5, "read_timeout": 20, "write_timeout": 20},
        echo=settings.DEBUG and False  # set to True for SQL debugging
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to initialize SQLAlchemy database engine: {e}")
    engine = None
    SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session per request."""
    if SessionLocal is None:
        raise RuntimeError("Database engine is not configured. Please check your .env credentials.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
