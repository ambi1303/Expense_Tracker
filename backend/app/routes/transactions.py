"""
Transaction routes for the expense tracker API.

This module provides endpoints for retrieving and exporting transactions.
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
import structlog

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.user import User
from app.services.transaction_service import (
    get_transactions,
    get_transaction_by_id,
    update_transaction_category,
    find_potential_duplicates,
    delete_transaction,
    batch_auto_categorize,
)
from app.schemas.transaction import (
    TransactionListResponse,
    TransactionResponse,
    TransactionFilterParams
)
from app.services.email_parser import TransactionType
from pydantic import BaseModel


logger = structlog.get_logger()


class TransactionCategoryUpdate(BaseModel):
    category: Optional[str] = None


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    account_label: Optional[str] = Query(None, description="Filter by account/card label"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum transaction amount"),
    sort_by: str = Query("transaction_date", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of transactions with optional filtering and sorting.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 100)
    - **transaction_type**: Filter by debit or credit
    - **start_date**: Filter transactions from this date onwards
    - **end_date**: Filter transactions up to this date
    - **merchant**: Filter by merchant name (case-insensitive partial match)
    - **bank_name**: Filter by bank name (case-insensitive partial match)
    - **min_amount**: Minimum transaction amount
    - **max_amount**: Maximum transaction amount
    - **sort_by**: Field to sort by (default: transaction_date)
    - **sort_order**: Sort order - asc or desc (default: desc)
    """
    logger.info(
        "list_transactions_request",
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
        filters={
            "transaction_type": transaction_type,
            "start_date": start_date,
            "end_date": end_date,
            "merchant": merchant,
            "bank_name": bank_name,
            "account_label": account_label,
            "category": category,
            "min_amount": min_amount,
            "max_amount": max_amount
        }
    )

    # Build filter params
    filters = TransactionFilterParams(
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        merchant=merchant,
        bank_name=bank_name,
        account_label=account_label,
        category=category,
        min_amount=min_amount,
        max_amount=max_amount
    )

    # Get transactions from service
    transactions, total = await get_transactions(
        db=db,
        user_id=current_user.id,
        filters=filters,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Convert to response models
    transaction_responses = [
        TransactionResponse(
            id=t.id,
            user_id=t.user_id,
            amount=t.amount,
            currency=t.currency,
            transaction_type=TransactionType(t.transaction_type),
            merchant=t.merchant,
            transaction_date=t.transaction_date,
            bank_name=t.bank_name,
            account_label=t.account_label,
            category=t.category,
            gmail_message_id=t.gmail_message_id,
            created_at=t.created_at
        )
        for t in transactions
    ]
    
    logger.info(
        "list_transactions_success",
        user_id=str(current_user.id),
        count=len(transaction_responses),
        total=total
    )
    
    # Calculate if there are more pages
    has_more = (skip + limit) < total
    
    return TransactionListResponse(
        transactions=transaction_responses,
        total=total,
        page=skip // limit,
        limit=limit,
        has_more=has_more
    )


@router.post("/auto-categorize")
async def trigger_auto_categorize(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-categorize all uncategorized transactions using merchant/description patterns."""
    updated = await batch_auto_categorize(db=db, user_id=current_user.id)
    return {"updated": updated, "message": f"Categorized {updated} transactions"}


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a transaction's category."""
    from uuid import UUID
    try:
        tid = UUID(transaction_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    txn = await update_transaction_category(db, tid, current_user.id, data.category)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse(
        id=txn.id,
        user_id=txn.user_id,
        amount=txn.amount,
        currency=txn.currency,
        transaction_type=TransactionType(txn.transaction_type),
        merchant=txn.merchant,
        transaction_date=txn.transaction_date,
        bank_name=txn.bank_name,
        account_label=txn.account_label,
        category=txn.category,
        gmail_message_id=txn.gmail_message_id,
        created_at=txn.created_at
    )


@router.get("/duplicates")
async def get_duplicates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get groups of potentially duplicate transactions."""
    groups = await find_potential_duplicates(db, current_user.id)
    return {
        "groups": [
            [
                {
                    "id": str(t.id),
                    "amount": str(t.amount),
                    "merchant": t.merchant,
                    "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
                    "category": t.category,
                    "gmail_message_id": (t.gmail_message_id[:20] + "...") if (t.gmail_message_id and len(t.gmail_message_id) > 20) else t.gmail_message_id,
                }
                for t in group
            ]
            for group in groups
        ]
    }


@router.delete("/{transaction_id}")
async def remove_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a transaction (e.g. duplicate)."""
    from uuid import UUID
    try:
        tid = UUID(transaction_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    ok = await delete_transaction(db, tid, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True}


@router.get("/export")
async def export_transactions_csv(
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    account_label: Optional[str] = Query(None, description="Filter by account/card label"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum transaction amount"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export transactions as CSV file.
    
    Applies the same filters as the list endpoint but returns all matching
    transactions (no pagination) in CSV format.
    
    - **transaction_type**: Filter by debit or credit
    - **start_date**: Filter transactions from this date onwards
    - **end_date**: Filter transactions up to this date
    - **merchant**: Filter by merchant name (case-insensitive partial match)
    - **bank_name**: Filter by bank name (case-insensitive partial match)
    - **min_amount**: Minimum transaction amount
    - **max_amount**: Maximum transaction amount
    """
    logger.info(
        "export_transactions_request",
        user_id=str(current_user.id),
        filters={
            "transaction_type": transaction_type,
            "start_date": start_date,
            "end_date": end_date,
            "merchant": merchant,
            "bank_name": bank_name,
            "min_amount": min_amount,
            "max_amount": max_amount
        }
    )
    
    # Build filter params
    filters = TransactionFilterParams(
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        merchant=merchant,
        bank_name=bank_name,
        account_label=account_label,
        category=category,
        min_amount=min_amount,
        max_amount=max_amount
    )

    # Get all transactions (no pagination for export)
    transactions, total = await get_transactions(
        db=db,
        user_id=current_user.id,
        filters=filters,
        skip=0,
        limit=10000,  # Large limit for export
        sort_by="transaction_date",
        sort_order="desc"
    )
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Date",
        "Type",
        "Amount",
        "Currency",
        "Merchant",
        "Bank",
        "Account/Card",
        "Category",
        "Created At"
    ])

    # Write data rows
    for t in transactions:
        writer.writerow([
            t.transaction_date.strftime("%Y-%m-%d %H:%M:%S"),
            t.transaction_type,
            str(t.amount),
            t.currency,
            t.merchant or "",
            t.bank_name or "",
            t.account_label or "",
            t.category or "",
            t.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    logger.info(
        "export_transactions_success",
        user_id=str(current_user.id),
        count=len(transactions)
    )
    
    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
