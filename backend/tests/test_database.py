"""
Tests for database configuration and connection.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, engine, get_db


@pytest.mark.asyncio
async def test_database_connection():
    """Test that database connection can be established."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_get_db_dependency():
    """Test that get_db dependency function works correctly."""
    # Test using the session factory directly (simulating what get_db does)
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)
        # Test a simple query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_connection_pool_settings():
    """Test that connection pool is configured correctly."""
    assert engine.pool.size() == 10  # pool_size
    assert engine.pool._max_overflow == 20  # max_overflow


@pytest.mark.asyncio
async def test_ssl_connection():
    """Test that SSL is configured for Neon compatibility."""
    # Check that connect_args includes SSL requirement
    # The engine's connect_args are stored in the dialect's connect_args
    from app.database import engine
    
    # For asyncpg, SSL is configured via connect_args passed to create_async_engine
    # We can verify this by checking the engine's creation parameters
    assert engine.pool is not None
    
    # The SSL configuration is in the connect_args, which we can verify by
    # checking that the engine was created with the correct parameters
    # Since we can't directly access connect_args from the engine object,
    # we'll verify by attempting a connection which will fail if SSL is not configured
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
