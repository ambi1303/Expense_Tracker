"""
Test database connection from the application's perspective.
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app.database import engine
from sqlalchemy import text

async def test_connection():
    """Test if the application can connect and query the database."""
    print("Testing database connection...")
    print(f"Database URL (masked): {str(engine.url).split('@')[1] if '@' in str(engine.url) else 'N/A'}")
    
    try:
        async with engine.connect() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            print("✅ Basic connection successful")
            
            # Check current database
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ Connected to database: {db_name}")
            
            # Check tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print(f"✅ Tables found: {', '.join(tables)}")
            
            # Try to query users table
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"✅ Users table accessible, count: {count}")
            
            print("\n🎉 All checks passed! Database is properly configured.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
