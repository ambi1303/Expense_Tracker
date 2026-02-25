"""
Sync routes for manual synchronization and sync history.

This module provides endpoints for triggering manual email synchronization
and retrieving sync history logs.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address
import structlog

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.user import User
from app.models.sync_log import SyncLog
from app.scheduler.sync_job import sync_user_emails
from pydantic import BaseModel, Field


logger = structlog.get_logger()
router = APIRouter(prefix="/sync", tags=["sync"])

# Rate limiter for manual sync endpoint
limiter = Limiter(key_func=get_remote_address)


class SyncResponse(BaseModel):
    """Response schema for manual sync operation."""
    success: bool = Field(..., description="Whether sync was successful")
    emails_processed: int = Field(..., ge=0, description="Number of emails processed")
    transactions_created: int = Field(..., ge=0, description="Number of transactions created")
    message: str = Field(..., description="Status message")
    error: str | None = Field(None, description="Error message if sync failed")


class SyncLogResponse(BaseModel):
    """Response schema for sync log entry."""
    id: str = Field(..., description="Sync log ID")
    status: str = Field(..., description="Sync status (success/failed)")
    emails_processed: int = Field(..., ge=0, description="Number of emails processed")
    errors: str | None = Field(None, description="Error details if any")
    created_at: datetime = Field(..., description="Sync timestamp")
    
    class Config:
        from_attributes = True


@router.post("/manual", response_model=SyncResponse)
@limiter.limit("3/minute")  # Max 3 syncs per minute per user
async def trigger_manual_sync(
    request: Request,  # Required for rate limiter
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger immediate email synchronization for the current user.
    
    Manually initiates the sync process that normally runs automatically every 15 minutes.
    This fetches new transaction emails from Gmail, parses them, and stores transactions
    in the database.
    
    Rate limited to 3 requests per minute to prevent abuse.
    
    Returns:
        SyncResponse with sync results including number of emails processed,
        transactions created, and any error messages.
    """
    logger.info("manual_sync_triggered", user_id=str(current_user.id))
    
    try:
        # Perform sync for current user
        sync_result = await sync_user_emails(current_user, db)
        
        # Create sync log entry
        sync_log = SyncLog(
            user_id=current_user.id,
            status="success" if sync_result['success'] else "failed",
            emails_processed=sync_result['emails_processed'],
            errors=sync_result['error']
        )
        db.add(sync_log)
        await db.commit()
        
        logger.info(
            "manual_sync_completed",
            user_id=str(current_user.id),
            success=sync_result['success'],
            emails_processed=sync_result['emails_processed'],
            transactions_created=sync_result['transactions_created']
        )
        
        if sync_result['success']:
            message = f"Successfully processed {sync_result['emails_processed']} emails and created {sync_result['transactions_created']} transactions"
        else:
            message = f"Sync failed: {sync_result['error']}"
        
        return SyncResponse(
            success=sync_result['success'],
            emails_processed=sync_result['emails_processed'],
            transactions_created=sync_result['transactions_created'],
            message=message,
            error=sync_result['error']
        )
        
    except Exception as e:
        logger.error(
            "manual_sync_error",
            user_id=str(current_user.id),
            error=str(e)
        )
        
        # Try to create error log
        try:
            sync_log = SyncLog(
                user_id=current_user.id,
                status="failed",
                emails_processed=0,
                errors=str(e)
            )
            db.add(sync_log)
            await db.commit()
        except Exception:
            pass
        
        return SyncResponse(
            success=False,
            emails_processed=0,
            transactions_created=0,
            message="Sync failed due to an error",
            error=str(e)
        )


@router.get("/history", response_model=List[SyncLogResponse])
async def get_sync_history(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of logs to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sync history for the current user.
    
    Returns a list of recent sync operations including their status, number of emails
    processed, and any error messages. Logs are ordered by timestamp in descending order
    (most recent first).
    
    - **limit**: Maximum number of log entries to return (1-100, default: 20)
    
    Returns:
        List of SyncLogResponse objects with sync history.
    """
    logger.info(
        "get_sync_history_request",
        user_id=str(current_user.id),
        limit=limit
    )
    
    # Query sync logs for current user
    query = select(SyncLog).where(
        SyncLog.user_id == current_user.id
    ).order_by(
        SyncLog.created_at.desc()
    ).limit(limit)
    
    result = await db.execute(query)
    sync_logs = result.scalars().all()
    
    # Convert to response models
    log_responses = [
        SyncLogResponse(
            id=str(log.id),
            status=log.status,
            emails_processed=log.emails_processed,
            errors=log.errors,
            created_at=log.created_at
        )
        for log in sync_logs
    ]
    
    logger.info(
        "get_sync_history_success",
        user_id=str(current_user.id),
        logs_returned=len(log_responses)
    )
    
    return log_responses
