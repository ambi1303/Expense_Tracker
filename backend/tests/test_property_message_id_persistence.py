"""
Property-based test for message ID persistence.

**Property 9: Message ID Persistence**

*For any* successfully processed email, the gmail_message_id should exist 
in the transactions table after processing completes.

**Validates: Requirements 3.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import delete

from app.services.transaction_service import create_transaction, get_processed_message_ids
from app.services.email_parser import ParsedTransaction, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.database import AsyncSessionLocal


# Strategy for generating valid parsed transactions
@st.composite
def parsed_transaction_strategy(draw):
    """Generate valid ParsedTransaction objects."""
    transaction_type = draw(st.sampled_from([TransactionType.DEBIT, TransactionType.CREDIT]))
    amount = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("999999.99"),
        places=2
    ))
    
    return ParsedTransaction(
        amount=amount,
        currency=draw(st.sampled_from(["INR", "USD", "EUR"])),
        transaction_type=transaction_type,
        merchant=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
            min_codepoint=32,
            max_codepoint=126
        ))),
        transaction_date=draw(st.datetimes(
            min_value=datetime(2020, 1, 1, tzinfo=timezone.utc),
            max_value=datetime(2025, 12, 31, tzinfo=timezone.utc),
            timezones=st.just(timezone.utc)
        )),
        bank_name=draw(st.sampled_from(["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Bank"]))
    )


# Strategy for generating unique Gmail message IDs
message_id_strategy = st.text(
    min_size=10,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        min_codepoint=48,
        max_codepoint=122
    )
)


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=5, deadline=None)
@given(
    parsed_transaction=parsed_transaction_strategy(),
    message_id=message_id_strategy
)
async def test_property_message_id_persistence(
    parsed_transaction,
    message_id
):
    """
    Property: For any successfully processed email, the gmail_message_id 
    should exist in the transactions table after processing completes.
    
    This test verifies that:
    1. After creating a transaction with a message_id, that message_id is persisted
    2. The message_id can be retrieved via get_processed_message_ids()
    3. This holds for any valid transaction data and message_id
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create transaction
        transaction = await create_transaction(
            db=session,
            user_id=test_user.id,
            parsed_transaction=parsed_transaction,
            message_id=message_id
        )
        
        # If transaction creation succeeded (not a duplicate)
        if transaction is not None:
            # Property: The message_id should now exist in the database
            processed_ids = await get_processed_message_ids(
                db=session,
                user_id=test_user.id
            )
            
            # Assert the message_id is in the set of processed IDs
            assert message_id in processed_ids, (
                f"Message ID '{message_id}' was not found in processed IDs after "
                f"successful transaction creation. Processed IDs: {processed_ids}"
            )
            
            # Additional verification: the transaction object should have the message_id
            assert transaction.gmail_message_id == message_id, (
                f"Transaction object has message_id '{transaction.gmail_message_id}' "
                f"but expected '{message_id}'"
            )
    
    finally:
        # Cleanup
        try:
            if test_user:
                await session.rollback()
                await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
                await session.execute(delete(User).where(User.id == test_user.id))
                await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()


@pytest.mark.asyncio
async def test_message_id_persistence_multiple_transactions():
    """
    Unit test: Verify message ID persistence with multiple transactions.
    
    This test ensures that multiple transactions for the same user all have
    their message IDs persisted correctly.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid4(),
            email=f"test_{uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        message_ids = [f"msg_{i}_{uuid4().hex[:8]}" for i in range(5)]
        
        # Create multiple transactions
        for i, msg_id in enumerate(message_ids):
            parsed_tx = ParsedTransaction(
                amount=Decimal("100.00") + Decimal(i),
                currency="INR",
                transaction_type=TransactionType.DEBIT,
                merchant=f"Merchant {i}",
                transaction_date=datetime.now(timezone.utc) - timedelta(days=i),
                bank_name="HDFC Bank"
            )
            
            transaction = await create_transaction(
                db=session,
                user_id=test_user.id,
                parsed_transaction=parsed_tx,
                message_id=msg_id
            )
            
            assert transaction is not None, f"Failed to create transaction {i}"
        
        # Verify all message IDs are persisted
        processed_ids = await get_processed_message_ids(
            db=session,
            user_id=test_user.id
        )
        
        for msg_id in message_ids:
            assert msg_id in processed_ids, (
                f"Message ID '{msg_id}' not found in processed IDs"
            )
        
        # Verify count
        assert len(processed_ids) == len(message_ids), (
            f"Expected {len(message_ids)} message IDs, but found {len(processed_ids)}"
        )
    
    finally:
        # Cleanup
        try:
            if test_user:
                await session.rollback()
                await session.execute(delete(Transaction).where(Transaction.user_id == test_user.id))
                await session.execute(delete(User).where(User.id == test_user.id))
                await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()


@pytest.mark.asyncio
async def test_message_id_persistence_different_users():
    """
    Unit test: Verify message ID persistence is user-specific.
    
    This test ensures that message IDs are correctly isolated per user.
    """
    session = AsyncSessionLocal()
    user1 = None
    user2 = None
    
    try:
        # Create test users
        user1 = User(
            id=uuid4(),
            email=f"test1_{uuid4()}@example.com",
            name="Test User 1",
            google_id=f"google1_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        user2 = User(
            id=uuid4(),
            email=f"test2_{uuid4()}@example.com",
            name="Test User 2",
            google_id=f"google2_{uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(user1)
        session.add(user2)
        await session.commit()
        
        msg_id_1 = f"user1_msg_{uuid4().hex[:8]}"
        msg_id_2 = f"user2_msg_{uuid4().hex[:8]}"
        
        parsed_tx = ParsedTransaction(
            amount=Decimal("100.00"),
            currency="INR",
            transaction_type=TransactionType.DEBIT,
            merchant="Test Merchant",
            transaction_date=datetime.now(timezone.utc),
            bank_name="HDFC Bank"
        )
        
        # Create transaction for user 1
        tx1 = await create_transaction(
            db=session,
            user_id=user1.id,
            parsed_transaction=parsed_tx,
            message_id=msg_id_1
        )
        
        # Create transaction for user 2
        tx2 = await create_transaction(
            db=session,
            user_id=user2.id,
            parsed_transaction=parsed_tx,
            message_id=msg_id_2
        )
        
        assert tx1 is not None
        assert tx2 is not None
        
        # Verify user 1's message IDs
        user1_ids = await get_processed_message_ids(
            db=session,
            user_id=user1.id
        )
        assert msg_id_1 in user1_ids
        assert msg_id_2 not in user1_ids
        
        # Verify user 2's message IDs
        user2_ids = await get_processed_message_ids(
            db=session,
            user_id=user2.id
        )
        assert msg_id_2 in user2_ids
        assert msg_id_1 not in user2_ids
    
    finally:
        # Cleanup
        try:
            if user1 or user2:
                await session.rollback()
                if user1:
                    await session.execute(delete(Transaction).where(Transaction.user_id == user1.id))
                    await session.execute(delete(User).where(User.id == user1.id))
                if user2:
                    await session.execute(delete(Transaction).where(Transaction.user_id == user2.id))
                    await session.execute(delete(User).where(User.id == user2.id))
                await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()
