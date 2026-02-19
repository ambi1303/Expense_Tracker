"""
Property-based test for duplicate email filtering.

Feature: gmail-expense-tracker
Property 7: Duplicate Email Filtering

**Validates: Requirements 3.2, 3.3**

For any sync operation, emails with message IDs that already exist in the 
transactions table should be skipped and not processed again.
"""

import pytest
from hypothesis import given, strategies as st, settings
from sqlalchemy import delete
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from app.models.transaction import Transaction
from app.models.user import User
from app.services.transaction_service import get_processed_message_ids, create_transaction
from app.services.email_parser import ParsedTransaction, TransactionType
from app.database import AsyncSessionLocal


# Strategy for generating message IDs
message_id_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=10,
    max_size=50
)


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=20)
@given(message_id=message_id_strategy)
async def test_processed_message_ids_includes_existing_transactions(message_id):
    """
    Property 7: Duplicate Email Filtering
    
    **Validates: Requirements 3.2, 3.3**
    
    For any transaction with a message ID, that message ID should appear in 
    the set of processed message IDs.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create transaction with message ID
        parsed = ParsedTransaction(
            amount=Decimal("100.00"),
            currency="INR",
            transaction_type=TransactionType.DEBIT,
            merchant="Test Merchant",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Test Bank"
        )
        
        await create_transaction(session, test_user.id, parsed, message_id)
        
        # Get processed message IDs
        processed_ids = await get_processed_message_ids(session, test_user.id)
        
        # Message ID should be in the set
        assert message_id in processed_ids, \
            f"Message ID '{message_id}' should be in processed IDs"
        
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


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=20)
@given(message_id=message_id_strategy)
async def test_duplicate_message_id_returns_none(message_id):
    """
    Property 7: Duplicate Email Filtering
    
    **Validates: Requirements 3.2, 3.3**
    
    For any message ID that already exists, attempting to create another 
    transaction with the same message ID should return None.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create first transaction
        parsed1 = ParsedTransaction(
            amount=Decimal("100.00"),
            currency="INR",
            transaction_type=TransactionType.DEBIT,
            merchant="Merchant 1",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Bank 1"
        )
        
        result1 = await create_transaction(session, test_user.id, parsed1, message_id)
        assert result1 is not None, "First transaction should be created"
        
        # Attempt to create second transaction with same message ID
        parsed2 = ParsedTransaction(
            amount=Decimal("200.00"),
            currency="INR",
            transaction_type=TransactionType.CREDIT,
            merchant="Merchant 2",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Bank 2"
        )
        
        result2 = await create_transaction(session, test_user.id, parsed2, message_id)
        
        # Second transaction should return None (duplicate)
        assert result2 is None, \
            "Second transaction with duplicate message ID should return None"
        
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


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=15)
@given(
    message_id1=message_id_strategy,
    message_id2=message_id_strategy
)
async def test_different_message_ids_both_processed(message_id1, message_id2):
    """
    Property 7: Duplicate Email Filtering
    
    **Validates: Requirements 3.2, 3.3**
    
    For any two different message IDs, both should be successfully processed 
    and appear in the processed IDs set.
    """
    # Skip if message IDs are the same
    if message_id1 == message_id2:
        return
    
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create first transaction
        parsed1 = ParsedTransaction(
            amount=Decimal("100.00"),
            currency="INR",
            transaction_type=TransactionType.DEBIT,
            merchant="Merchant 1",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Bank 1"
        )
        
        result1 = await create_transaction(session, test_user.id, parsed1, message_id1)
        assert result1 is not None, "First transaction should be created"
        
        # Create second transaction with different message ID
        parsed2 = ParsedTransaction(
            amount=Decimal("200.00"),
            currency="INR",
            transaction_type=TransactionType.CREDIT,
            merchant="Merchant 2",
            transaction_date=datetime.now(timezone.utc),
            bank_name="Bank 2"
        )
        
        result2 = await create_transaction(session, test_user.id, parsed2, message_id2)
        assert result2 is not None, "Second transaction should be created"
        
        # Get processed message IDs
        processed_ids = await get_processed_message_ids(session, test_user.id)
        
        # Both message IDs should be in the set
        assert message_id1 in processed_ids, \
            f"Message ID 1 '{message_id1}' should be in processed IDs"
        assert message_id2 in processed_ids, \
            f"Message ID 2 '{message_id2}' should be in processed IDs"
        
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


@pytest.mark.property
@pytest.mark.asyncio
async def test_empty_processed_ids_for_new_user():
    """
    Property 7: Duplicate Email Filtering
    
    **Validates: Requirements 3.2, 3.3**
    
    For any new user with no transactions, the processed message IDs set 
    should be empty.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Get processed message IDs (should be empty)
        processed_ids = await get_processed_message_ids(session, test_user.id)
        
        # Should be empty set
        assert len(processed_ids) == 0, \
            "New user should have no processed message IDs"
        assert isinstance(processed_ids, set), \
            "Should return a set"
        
    finally:
        # Cleanup
        try:
            if test_user:
                await session.rollback()
                await session.execute(delete(User).where(User.id == test_user.id))
                await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()


@pytest.mark.property
@pytest.mark.asyncio
@settings(max_examples=10)
@given(message_ids=st.lists(message_id_strategy, min_size=2, max_size=5, unique=True))
async def test_multiple_message_ids_all_tracked(message_ids):
    """
    Property 7: Duplicate Email Filtering
    
    **Validates: Requirements 3.2, 3.3**
    
    For any list of unique message IDs, all should be tracked in the 
    processed IDs set.
    """
    session = AsyncSessionLocal()
    test_user = None
    
    try:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4()}@example.com",
            name="Test User",
            google_id=f"google_{uuid.uuid4()}",
            refresh_token_encrypted="encrypted_token"
        )
        session.add(test_user)
        await session.commit()
        
        # Create transactions for each message ID
        for i, message_id in enumerate(message_ids):
            parsed = ParsedTransaction(
                amount=Decimal(f"{100 + i}.00"),
                currency="INR",
                transaction_type=TransactionType.DEBIT,
                merchant=f"Merchant {i}",
                transaction_date=datetime.now(timezone.utc),
                bank_name=f"Bank {i}"
            )
            
            result = await create_transaction(session, test_user.id, parsed, message_id)
            assert result is not None, f"Transaction {i} should be created"
        
        # Get processed message IDs
        processed_ids = await get_processed_message_ids(session, test_user.id)
        
        # All message IDs should be in the set
        for message_id in message_ids:
            assert message_id in processed_ids, \
                f"Message ID '{message_id}' should be in processed IDs"
        
        # Count should match
        assert len(processed_ids) == len(message_ids), \
            f"Should have {len(message_ids)} processed IDs, got {len(processed_ids)}"
        
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
