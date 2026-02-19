"""
Script to identify and optionally delete transactions with future dates.

This script finds transactions that have dates in the future (which shouldn't exist)
and allows you to review and delete them.
"""

import asyncio
import os
from datetime import datetime, timezone
from sqlalchemy import select
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.database import AsyncSessionLocal
from app.models.transaction import Transaction


async def find_future_transactions():
    """Find all transactions with dates in the future."""
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        
        # Query for transactions with future dates
        query = select(Transaction).where(Transaction.transaction_date > now)
        result = await session.execute(query)
        future_transactions = result.scalars().all()
        
        if not future_transactions:
            print("✅ No transactions with future dates found!")
            return
        
        print(f"\n⚠️  Found {len(future_transactions)} transaction(s) with future dates:\n")
        
        for txn in future_transactions:
            print(f"ID: {txn.id}")
            print(f"Date: {txn.transaction_date}")
            print(f"Amount: {txn.amount} {txn.currency}")
            print(f"Type: {txn.transaction_type}")
            print(f"Merchant: {txn.merchant}")
            print(f"Gmail Message ID: {txn.gmail_message_id}")
            print(f"Created At: {txn.created_at}")
            print("-" * 60)
        
        # Ask user if they want to delete these transactions
        response = input("\nDo you want to DELETE these transactions? (yes/no): ")
        
        if response.lower() == 'yes':
            for txn in future_transactions:
                await session.delete(txn)
            await session.commit()
            print(f"\n✅ Deleted {len(future_transactions)} transaction(s) with future dates.")
        else:
            print("\n❌ No transactions were deleted.")


if __name__ == "__main__":
    asyncio.run(find_future_transactions())
