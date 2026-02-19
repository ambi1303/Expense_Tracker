"""
Property-based test for Gmail Message ID uniqueness constraint.

Feature: gmail-expense-tracker
Property 1: Gmail Message ID Uniqueness (Idempotency)

**Validates: Requirements 1.8, 3.3**

For any gmail_message_id, attempting to insert a second transaction with the 
same message ID should fail with a unique constraint violation, ensuring no 
duplicate transaction processing.
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import uuid

from app.models.transaction import Transaction, TransactionTypeEnum
from app.models.user import User
from app.database import AsyncSessionLocal


# Strategy for generating valid gmail message IDs
gmail_message_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, blacklist_categories=('Cc', 'Cs')),
    min_size=10,
    max_size=50
)

# Strategy for generating transaction amounts
amount_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2
)

# Strategy for generating transaction types
transaction_type_strategy = st.sampled_from([TransactionTypeEnum.DEBIT, TransactionTypeEnum.CREDIT])


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=10)  # Using 10 examples for faster test execution
@given(
    message_id=gmail_message_id_strategy,
    amount=amount_strategy,
    transaction_type=transaction_type_strategy
)
async def test_duplicate_gmail_message_id_rejected(message_id, amount, transaction_type):
    """
    Property 1: Gmail Message ID Uniqueness (Idempotency)
    
    **Validates: Requirements 1.8, 3.3**
    
    For any gmail_message_id, attempting to insert a second transaction with 
    the same message ID should fail with a unique constraint violation.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create a test user first
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create first transaction with the message ID
        transaction1 = Transaction(
            id=uuid.uuid4(),
            user_id=test_user.id,
            amount=amount,
            currency="INR",
            transaction_type=transaction_type,
            merchant="Test Merchant",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Test Bank",
            gmail_message_id=message_id
        )
        session.add(transaction1)
        await session.commit()
        
        # Attempt to create a second transaction with the same message ID
        # This should fail with IntegrityError due to unique constraint
        transaction2 = Transaction(
            id=uuid.uuid4(),
            user_id=test_user.id,
            amount=amount + Decimal("10.00"),  # Different amount
            currency="INR",
            transaction_type=transaction_type,
            merchant="Different Merchant",
            transaction_date=datetime.now(timezone.utc) + timedelta(days=1),
            bank_name="Different Bank",
            gmail_message_id=message_id  # Same message ID - should fail
        )
        session.add(transaction2)
        
        # This commit should raise IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            await session.commit()
        
        # Verify the error is specifically about the unique constraint
        error_msg = str(exc_info.value).lower()
        assert "gmail_message_id" in error_msg or "unique" in error_msg, \
            f"Expected unique constraint error for gmail_message_id, got: {exc_info.value}"
            
    finally:
        # Cleanup: delete test data to avoid conflicts in subsequent test iterations
        try:
            if test_user:
                # Rollback any pending transaction first
                await session.rollback()
                
                # Delete transactions for this user
                await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
                # Delete the test user
                await session.execute(delete(User).where(User.id == test_user.id))
                await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()
