"""
SQLAlchemy engine + session management.

Uses the standard FastAPI dependency-injection pattern: `get_db()` yields a
session per-request and always closes it, even if the request raises.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

# `pool_pre_ping` avoids "server has gone away" errors on idle connections.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
