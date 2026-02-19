"""
Pytest configuration and shared fixtures
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables from .env file (or .evn if that's what exists)
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists(".evn"):
    load_dotenv(".evn")

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.
    This allows session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing FastAPI endpoints
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Create database tables before running tests and drop them after.
    This runs once per test session.
    """
    from app.database import engine, Base
    from app.models.user import User
    from app.models.transaction import Transaction
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Dispose of the engine
    await engine.dispose()


@pytest.fixture(scope="function", autouse=True)
async def cleanup_transactions():
    """
    Clean up transactions and users after each test to ensure test isolation.
    """
    yield
    
    # Clean up after test
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            # Delete all transactions and users
            await session.execute("DELETE FROM transactions")
            await session.execute("DELETE FROM users")
            await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()
