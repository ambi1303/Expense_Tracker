"""
Verify database state and fix migration issues.

This script:
1. Checks what tables actually exist in the database
2. Checks what Alembic thinks is applied
3. Resets and re-runs migrations if there's a mismatch
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# Remove sslmode and channel_binding parameters
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
parsed = urlparse(DATABASE_URL)
query_params = parse_qs(parsed.query)
query_params.pop('sslmode', None)
query_params.pop('channel_binding', None)
new_query = urlencode(query_params, doseq=True)
DATABASE_URL = urlunparse((
    parsed.scheme,
    parsed.netloc,
    parsed.path,
    parsed.params,
    new_query,
    parsed.fragment
))

async def check_database():
    """Check what tables exist and what migrations are recorded."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            # Check what tables exist
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            print("=== EXISTING TABLES ===")
            if tables:
                for table in tables:
                    print(f"  - {table}")
            else:
                print("  No tables found!")
            
            # Check alembic version
            if 'alembic_version' in tables:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = [row[0] for row in result]
                print("\n=== ALEMBIC VERSIONS ===")
                for version in versions:
                    print(f"  - {version}")
            else:
                print("\n=== ALEMBIC VERSIONS ===")
                print("  alembic_version table does not exist")
            
            # Check if required tables exist
            required_tables = ['users', 'transactions', 'sync_logs']
            missing_tables = [t for t in required_tables if t not in tables]
            
            print("\n=== DIAGNOSIS ===")
            if missing_tables:
                print(f"  ❌ Missing tables: {', '.join(missing_tables)}")
                print("  ⚠️  Database state is inconsistent with migrations")
                print("\n=== RECOMMENDED ACTION ===")
                print("  Run: python reset_and_migrate.py")
                return False
            else:
                print("  ✅ All required tables exist")
                return True
                
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_database())
