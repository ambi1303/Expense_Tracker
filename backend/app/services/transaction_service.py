"""
Transaction service for database operations.

This module provides functions for creating, retrieving, and managing transactions
in the database.
"""

from typing import List, Optional, Set
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
import structlog

from app.models.transaction import Transaction
from app.services.email_parser import ParsedTransaction
from app.schemas.transaction import TransactionFilterParams


logger = structlog.get_logger()

# Allowed sort fields whitelist for security
ALLOWED_SORT_FIELDS = {
    'transaction_date',
    'amount',
    'merchant',
    'bank_name',
    'account_label',
    'transaction_type',
    'created_at'
}


async def create_transaction(
    db: AsyncSession,
    user_id: UUID,
    parsed_transaction: ParsedTransaction,
    message_id: str
) -> Optional[Transaction]:
    """
    Create a new transaction in the database.
    
    Args:
        db: Database session.
        user_id: User ID who owns the transaction.
        parsed_transaction: Parsed transaction data from email.
        message_id: Gmail message ID.
        
    Returns:
        Created Transaction object, or None if duplicate message_id.
        
    Raises:
        ValueError: If input validation fails.
        IntegrityError: If unique constraint is violated (handled gracefully).
    """
    # Input validation
    if not message_id or not message_id.strip():
        raise ValueError("message_id cannot be empty")
    
    if parsed_transaction.amount <= 0:
        raise ValueError(f"amount must be positive, got {parsed_transaction.amount}")
    
    if parsed_transaction.currency not in ["INR", "USD", "EUR", "GBP"]:
        logger.warning("unusual_currency", currency=parsed_transaction.currency)
    
    # Validate date is not too far in the future (allow up to 1 day for timezone differences)
    from datetime import timezone, timedelta
    max_future_date = datetime.now(timezone.utc) + timedelta(days=1)
    if parsed_transaction.transaction_date > max_future_date:
        raise ValueError(
            f"transaction_date cannot be in the future: {parsed_transaction.transaction_date}"
        )
    
    # Validate date is not too far in the past (10 years)
    min_past_date = datetime.now(timezone.utc) - timedelta(days=365 * 10)
    if parsed_transaction.transaction_date < min_past_date:
        logger.warning(
            "very_old_transaction",
            transaction_date=parsed_transaction.transaction_date.isoformat()
        )
    
    logger.info(
        "create_transaction_started",
        user_id=str(user_id),
        message_id=message_id,
        amount=str(parsed_transaction.amount)
    )
    
    try:
        # Create transaction object
        transaction = Transaction(
            user_id=user_id,
            amount=parsed_transaction.amount,
            currency=parsed_transaction.currency,
            transaction_type=parsed_transaction.transaction_type.value,
            merchant=parsed_transaction.merchant,
            transaction_date=parsed_transaction.transaction_date,
            bank_name=parsed_transaction.bank_name,
            account_label=parsed_transaction.account_label,
            gmail_message_id=message_id,
            category=parsed_transaction.category,
            payment_method=parsed_transaction.payment_method,
            upi_reference=parsed_transaction.upi_reference,
            raw_snippet=parsed_transaction.raw_snippet
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        logger.info(
            "create_transaction_success",
            transaction_id=str(transaction.id),
            user_id=str(user_id)
        )
        
        return transaction
        
    except IntegrityError as e:
        await db.rollback()
        
        # Check if it's a duplicate message_id error
        if 'gmail_message_id' in str(e).lower() or 'unique' in str(e).lower():
            logger.warning(
                "create_transaction_duplicate",
                message_id=message_id,
                user_id=str(user_id)
            )
            return None
        else:
            # Re-raise if it's a different integrity error
            logger.error(
                "create_transaction_integrity_error",
                error=str(e),
                user_id=str(user_id)
            )
            raise
    
    except Exception as e:
        await db.rollback()
        logger.error(
            "create_transaction_failed",
            error=str(e),
            user_id=str(user_id)
        )
        raise


async def get_transactions(
    db: AsyncSession,
    user_id: UUID,
    filters: Optional[TransactionFilterParams] = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "transaction_date",
    sort_order: str = "desc"
) -> tuple[List[Transaction], int]:
    """
    Get paginated transactions for a user with optional filtering.
    
    Args:
        db: Database session.
        user_id: User ID to fetch transactions for.
        filters: Optional filter parameters.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return (max 100).
        sort_by: Field to sort by (default: transaction_date).
        sort_order: Sort order - 'asc' or 'desc' (default: desc).
        
    Returns:
        Tuple of (list of transactions, total count).
    """
    logger.info(
        "get_transactions_started",
        user_id=str(user_id),
        skip=skip,
        limit=limit
    )
    
    # Validate sort_by parameter against whitelist
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise ValueError(f"Invalid sort_by field: {sort_by}. Allowed: {ALLOWED_SORT_FIELDS}")
    
    # Enforce maximum limit
    limit = min(limit, 100)
    
    # Build base query
    query = select(Transaction).where(Transaction.user_id == user_id)
    
    # Apply filters
    if filters:
        if filters.transaction_type:
            query = query.where(Transaction.transaction_type == filters.transaction_type.value)
        
        if filters.start_date:
            # Convert string date to timezone-aware datetime (UTC)
            from datetime import datetime, timezone
            start_dt = datetime.strptime(filters.start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.where(Transaction.transaction_date >= start_dt)
        
        if filters.end_date:
            # Convert string date to timezone-aware datetime (end of day, UTC)
            from datetime import datetime, timezone, timedelta
            end_dt = datetime.strptime(filters.end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
            query = query.where(Transaction.transaction_date < end_dt)
        
        if filters.merchant:
            query = query.where(Transaction.merchant.ilike(f"%{filters.merchant}%"))
        
        if filters.bank_name:
            query = query.where(Transaction.bank_name.ilike(f"%{filters.bank_name}%"))

        if filters.account_label:
            query = query.where(Transaction.account_label.ilike(f"%{filters.account_label}%"))
        
        if filters.min_amount:
            query = query.where(Transaction.amount >= filters.min_amount)
        
        if filters.max_amount:
            query = query.where(Transaction.amount <= filters.max_amount)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    if sort_order.lower() == "asc":
        query = query.order_by(getattr(Transaction, sort_by).asc())
    else:
        query = query.order_by(getattr(Transaction, sort_by).desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    logger.info(
        "get_transactions_success",
        user_id=str(user_id),
        count=len(transactions),
        total=total
    )
    
    return list(transactions), total


async def get_processed_message_ids(
    db: AsyncSession,
    user_id: UUID
) -> Set[str]:
    """
    Get set of already processed Gmail message IDs for a user.
    
    This is used for duplicate checking during email sync to avoid
    processing the same email multiple times.
    
    Args:
        db: Database session.
        user_id: User ID to fetch message IDs for.
        
    Returns:
        Set of Gmail message IDs that have been processed.
    """
    logger.info("get_processed_message_ids_started", user_id=str(user_id))
    
    # Query for all message IDs for this user
    query = select(Transaction.gmail_message_id).where(
        Transaction.user_id == user_id
    )
    
    result = await db.execute(query)
    message_ids = result.scalars().all()
    
    message_id_set = set(message_ids)
    
    logger.info(
        "get_processed_message_ids_success",
        user_id=str(user_id),
        count=len(message_id_set)
    )
    
    return message_id_set


async def get_transaction_by_id(
    db: AsyncSession,
    transaction_id: UUID,
    user_id: UUID
) -> Optional[Transaction]:
    """
    Get a specific transaction by ID.
    
    Args:
        db: Database session.
        transaction_id: Transaction ID to fetch.
        user_id: User ID (for authorization check).
        
    Returns:
        Transaction object if found and belongs to user, None otherwise.
    """
    query = select(Transaction).where(
        and_(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        )
    )
    
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()
    
    return transaction


async def delete_transaction(
    db: AsyncSession,
    transaction_id: UUID,
    user_id: UUID
) -> bool:
    """
    Delete a transaction.
    
    Args:
        db: Database session.
        transaction_id: Transaction ID to delete.
        user_id: User ID (for authorization check).
        
    Returns:
        True if deleted, False if not found.
    """
    transaction = await get_transaction_by_id(db, transaction_id, user_id)
    
    if not transaction:
        return False
    
    await db.delete(transaction)
    await db.commit()
    
    logger.info(
        "delete_transaction_success",
        transaction_id=str(transaction_id),
        user_id=str(user_id)
    )
    
    return True
