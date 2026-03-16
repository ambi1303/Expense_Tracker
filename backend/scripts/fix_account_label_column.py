"""
Add account_label column to transactions table if missing.
Run from backend dir: python scripts/fix_account_label_column.py
"""
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

async def main():
    from sqlalchemy import text
    from app.database import engine

    async with engine.begin() as conn:
        r = await conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'transactions' AND column_name = 'account_label'
        """))
        row = r.fetchone()
        if row is not None:
            print("account_label already exists.")
        else:
            await conn.execute(text("ALTER TABLE transactions ADD COLUMN account_label VARCHAR(128)"))
            await conn.execute(text("CREATE INDEX ix_transactions_account_label ON transactions(account_label)"))
            print("Added account_label column and index.")

        r2 = await conn.execute(text("""
            SELECT 1 FROM information_schema.tables WHERE table_name = 'budgets'
        """))
        if r2.fetchone() is not None:
            print("budgets table already exists.")
        else:
            await conn.execute(text("""
                CREATE TABLE budgets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    category VARCHAR(100) NOT NULL,
                    amount NUMERIC(12,2) NOT NULL,
                    period VARCHAR(20) NOT NULL DEFAULT 'monthly',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            await conn.execute(text("CREATE INDEX ix_budgets_user_id ON budgets(user_id)"))
            await conn.execute(text("CREATE INDEX ix_budgets_category ON budgets(category)"))
            print("Created budgets table.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
