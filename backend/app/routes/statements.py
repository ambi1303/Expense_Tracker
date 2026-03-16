"""
Statement upload routes for bank and credit card statements (PDF/CSV).

Allows users to upload statement files and import transactions,
as an alternative to Gmail-based analysis.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.user import User
from app.services.statement_parser import (
    parse_csv_statement,
    parse_pdf_statement,
    MAX_CSV_SIZE,
    MAX_PDF_SIZE,
    ALLOWED_EXTENSIONS,
)
from app.services.transaction_service import create_transaction


logger = structlog.get_logger()
router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a bank or credit card statement (PDF or CSV).
    Parses the file, extracts transactions, and saves them to the user's account.
    Uses synthetic message IDs (stmt_{upload_id}_{idx}) to avoid duplicates.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    size = len(content)
    if ext == ".csv" and size > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"CSV file too large. Max size: {MAX_CSV_SIZE // 1024 // 1024} MB",
        )
    if ext == ".pdf" and size > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"PDF file too large. Max size: {MAX_PDF_SIZE // 1024 // 1024} MB",
        )

    if ext == ".csv":
        transactions = parse_csv_statement(content, file.filename)
    else:
        transactions = parse_pdf_statement(content, file.filename)

    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No transactions could be parsed from this file. Check the format.",
        )

    upload_id = str(uuid.uuid4())
    created = 0
    skipped = 0

    for idx, pt in enumerate(transactions):
        message_id = f"stmt_{upload_id}_{idx}"
        try:
            txn = await create_transaction(
                db=db,
                user_id=current_user.id,
                parsed_transaction=pt,
                message_id=message_id,
            )
            if txn:
                created += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(
                "statement_transaction_failed",
                upload_id=upload_id,
                index=idx,
                error=str(e),
            )
            skipped += 1

    return {
        "upload_id": upload_id,
        "parsed": len(transactions),
        "created": created,
        "skipped": skipped,
    }


@router.post("/preview")
async def preview_statement(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Preview parsed transactions from an uploaded statement without saving.
    Returns the extracted transactions for review before import.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    size = len(content)
    if ext == ".csv" and size > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"CSV file too large. Max size: {MAX_CSV_SIZE // 1024 // 1024} MB",
        )
    if ext == ".pdf" and size > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"PDF file too large. Max size: {MAX_PDF_SIZE // 1024 // 1024} MB",
        )

    if ext == ".csv":
        transactions = parse_csv_statement(content, file.filename)
    else:
        transactions = parse_pdf_statement(content, file.filename)

    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No transactions could be parsed from this file. Check the format.",
        )

    preview = [
        {
            "amount": str(t.amount),
            "currency": t.currency,
            "transaction_type": t.transaction_type.value,
            "merchant": t.merchant,
            "transaction_date": t.transaction_date.isoformat(),
        }
        for t in transactions[:50]
    ]

    return {
        "count": len(transactions),
        "preview": preview,
        "truncated": len(transactions) > 50,
    }
