"""
Database configuration and session management.

Provides async SQLAlchemy 2.0 setup with connection pooling and session management.
"""

from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine = create_async_engine(
    str(settings.DATABASE_URL),
    poolclass=NullPool,  # Use NullPool for async engine compatibility
    pool_pre_ping=settings.POOL_PRE_PING,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections every hour
    echo=settings.LOG_LEVEL == "DEBUG",  # Log SQL queries in debug mode
    future=True,
    # Connection arguments for PostgreSQL optimization
    connect_args={
        "server_settings": {
            "jit": "off",  # Disable JIT for faster connection times
        },
        # Temporarily disable SSL for asyncpg compatibility
        # "ssl": None  # Can be configured later for production
    }
)

# Create session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)

# Import the shared Base from models
from app.models.base import Base


async def create_db_and_tables():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        # Import essential models only to avoid conflicts during initial setup
        from app.models import user, role, permission  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Get database session for use in services.
    
    Returns:
        AsyncSession: Database session
    """
    return async_session()