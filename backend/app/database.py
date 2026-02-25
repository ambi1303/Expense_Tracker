"""
Database configuration for Neon PostgreSQL with async SQLAlchemy.

This module sets up the async database engine, session factory, and provides
the dependency injection function for FastAPI routes.
"""

import os
from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# Load environment variables - critical for uvicorn --reload mode
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Convert PostgreSQL URL to asyncpg format if needed
# Neon provides postgresql:// but we need postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# Parse URL to remove sslmode and channel_binding query parameters
# asyncpg doesn't accept these parameters - SSL is configured via connect_args
parsed = urlparse(DATABASE_URL)
query_params = parse_qs(parsed.query)

# Remove sslmode and channel_binding from query params
query_params.pop('sslmode', None)
query_params.pop('channel_binding', None)

# Reconstruct URL without these parameters
new_query = urlencode(query_params, doseq=True)
DATABASE_URL = urlunparse((
    parsed.scheme,
    parsed.netloc,
    parsed.path,
    parsed.params,
    new_query,
    parsed.fragment
))

# Create async engine with Neon-optimized connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging in development
    pool_size=10,  # Number of connections to maintain in the pool
    max_overflow=20,  # Maximum number of connections that can be created beyond pool_size
    pool_pre_ping=True,  # Verify connections before using them (handles Neon idle timeout)
    pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
    connect_args={
        "ssl": "require",  # Neon requires SSL connections
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
    autocommit=False,
    autoflush=False,
)

# Base class for all ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for FastAPI routes to get database sessions.
    
    Yields:
        AsyncSession: Database session that will be automatically closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
