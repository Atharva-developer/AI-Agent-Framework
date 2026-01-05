"""
Database initialization and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, DATABASE_ECHO
from src.database.models import Base

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=DATABASE_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables initialized.")


def get_session():
    """Get a database session."""
    return SessionLocal()


def close_session(session):
    """Close a database session."""
    session.close()
