"""
Sync job for automated email synchronization.

This module implements the background job that periodically fetches and processes
Gmail emails for all active users, extracting transaction data and storing it
in the database.
"""

from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from asyncio import Lock
import structlog

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.sync_log import SyncLog
from app.auth.encryption import decrypt_refresh_token
from app.auth.oauth import refresh_access_token_async
from app.services.gmail_service import fetch_transaction_emails, get_email_content
from app.services.email_parser import parse_emails
from app.services.transaction_service import create_transaction, get_processed_message_ids


logger = structlog.get_logger()

# Per-user sync locks to prevent concurrent syncs
_user_sync_locks: Dict[UUID, Lock] = {}
_locks_dict_lock = Lock()


async def get_user_sync_lock(user_id: UUID) -> Lock:
    """
    Get or create sync lock for a specific user.
    
    Args:
        user_id: User ID to get lock for.
        
    Returns:
        asyncio.Lock for the user.
    """
    async with _locks_dict_lock:
        if user_id not in _user_sync_locks:
            _user_sync_locks[user_id] = Lock()
        return _user_sync_locks[user_id]


async def sync_user_emails(
    user: User,
    session: AsyncSession,
    from_date: Optional[str] = None,
    full_sync: bool = False
) -> dict:
    """
    Sync emails for a single user with incremental sync and concurrency control.

    Fetches transaction emails from Gmail, parses them, and stores transactions
    in the database. Uses a fresh DB session for work after the Gmail fetch to
    avoid connection timeout during long fetches (7k+ emails can take minutes).

    Args:
        user: User object to sync emails for.
        session: Database session (used only for initial last_sync query).
        from_date: Optional date string (YYYY-MM-DD). If set, fetch emails from this date.
        full_sync: If True, fetch all emails (no date filter). Use after clearing data.

    Returns:
        Dict with sync results: {
            'success': bool,
            'emails_processed': int,
            'transactions_created': int,
            'error': str or None
        }
    """
    user_id = user.id  # Capture for use after long operations
    logger.info("sync_user_emails_started", user_id=str(user_id), email=user.email)
    
    # Acquire user-specific lock to prevent concurrent syncs
    lock = await get_user_sync_lock(user_id)
    
    if lock.locked():
        logger.warning("sync_already_in_progress", user_id=str(user_id))
        return {
            'success': False,
            'emails_processed': 0,
            'transactions_created': 0,
            'error': 'Sync already in progress for this user'
        }
    
    async with lock:
        try:
            # Decrypt and refresh access token (async)
            refresh_token = decrypt_refresh_token(user.refresh_token_encrypted)
            access_token = await refresh_access_token_async(refresh_token)
            
            logger.info("access_token_refreshed", user_id=str(user_id))
            
            # Determine which date to use for Gmail fetch (quick DB query)
            if full_sync:
                sync_time_used = None
                logger.info("full_sync_requested", user_id=str(user_id))
            elif from_date:
                try:
                    parsed = datetime.strptime(from_date.strip(), "%Y-%m-%d")
                    sync_time_used = parsed.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
                    logger.info("from_date_override", user_id=str(user_id), from_date=from_date)
                except ValueError:
                    logger.warning("invalid_from_date", from_date=from_date)
                    sync_time_used = None
            else:
                last_sync_query = select(SyncLog.created_at).where(
                    and_(
                        SyncLog.user_id == user_id,
                        SyncLog.status == "success"
                    )
                ).order_by(SyncLog.created_at.desc()).limit(1)
                result = await session.execute(last_sync_query)
                sync_time_used = result.scalar_one_or_none()
                logger.info("last_sync_time_queried", user_id=str(user_id), last_sync_time=sync_time_used)

            # Fetch emails from Gmail (can take minutes for 7k+ emails - no DB session used)
            emails = await fetch_transaction_emails(access_token, sync_time_used)
            
            logger.info(
                "emails_fetched",
                user_id=str(user_id),
                email_count=len(emails)
            )
            
            # Use a FRESH session for DB work after long fetch - avoids "connection is closed"
            async with AsyncSessionLocal() as db:
                processed_ids = await get_processed_message_ids(db, user_id)
                
                # Filter out already processed emails
                new_emails = [e for e in emails if e['message_id'] not in processed_ids]
                
                logger.info(
                    "emails_filtered",
                    user_id=str(user_id),
                    new_emails=len(new_emails),
                    already_processed=len(emails) - len(new_emails)
                )
                
                # Process each new email
                transactions_created = 0
                emails_processed = 0
                
                for email in new_emails:
                    try:
                        parsed_list = parse_emails(
                            email.get('subject', ''),
                            email.get('body', '')
                        )
                        
                        for i, parsed in enumerate(parsed_list):
                            # Use message_id for first; message_id_0, message_id_1 for multiples
                            msg_id = email['message_id'] if i == 0 else f"{email['message_id']}_{i}"
                            transaction = await create_transaction(
                                db=db,
                                user_id=user_id,
                                parsed_transaction=parsed,
                                message_id=msg_id
                            )
                            if transaction:
                                transactions_created += 1
                                logger.info(
                                    "transaction_created",
                                    user_id=str(user_id),
                                    transaction_id=str(transaction.id),
                                    message_id=msg_id
                                )
                            else:
                                logger.warning(
                                    "transaction_duplicate_skipped",
                                    user_id=str(user_id),
                                    message_id=msg_id
                                )
                        
                        emails_processed += 1
                        
                    except Exception as e:
                        logger.error(
                            "email_processing_error",
                            user_id=str(user_id),
                            message_id=email.get('message_id'),
                            error=str(e)
                        )
                        # Continue processing other emails
                        continue
                
                logger.info(
                    "sync_user_emails_success",
                    user_id=str(user_id),
                    emails_processed=emails_processed,
                    transactions_created=transactions_created
                )
            
            return {
                'success': True,
                'emails_processed': emails_processed,
                'transactions_created': transactions_created,
                'error': None
            }
            
        except Exception as e:
            logger.error(
                "sync_user_emails_failed",
                user_id=str(user_id),
                error=str(e)
            )
            
            return {
                'success': False,
                'emails_processed': 0,
                'transactions_created': 0,
                'error': str(e)
            }


async def sync_all_users():
    """
    Sync emails for all active users.
    
    Fetches all users from the database and processes their emails one by one.
    Errors for individual users are logged but don't stop processing of other users.
    Creates sync log entries for each user.
    """
    logger.info("sync_all_users_started")
    
    try:
        # Fetch all users (separate session for user list)
        async with AsyncSessionLocal() as list_session:
            result = await list_session.execute(select(User))
            users = result.scalars().all()
        
        logger.info("users_fetched", user_count=len(users))
        total_processed = 0
        total_errors = 0
        
        # Process each user with a fresh session (avoids long-lived connections)
        for user in users:
            try:
                async with AsyncSessionLocal() as session:
                    sync_result = await sync_user_emails(user, session)
                    
                    sync_log = SyncLog(
                        user_id=user.id,
                        status="success" if sync_result['success'] else "failed",
                        emails_processed=sync_result['emails_processed'],
                        errors=sync_result['error']
                    )
                    session.add(sync_log)
                    await session.commit()
                
                if sync_result['success']:
                    total_processed += 1
                else:
                    total_errors += 1
                
                logger.info(
                    "user_sync_completed",
                    user_id=str(user.id),
                    success=sync_result['success'],
                    emails_processed=sync_result['emails_processed']
                )
                
            except Exception as e:
                logger.error("user_sync_error", user_id=str(user.id), error=str(e))
                try:
                    async with AsyncSessionLocal() as session:
                        sync_log = SyncLog(
                            user_id=user.id,
                            status="failed",
                            emails_processed=0,
                            errors=str(e)
                        )
                        session.add(sync_log)
                        await session.commit()
                except Exception as log_error:
                    logger.error("sync_log_creation_failed", user_id=str(user.id), error=str(log_error))
                total_errors += 1
        
        logger.info(
            "sync_all_users_completed",
            total_users=len(users),
            successful=total_processed,
            failed=total_errors
        )
        
    except Exception as e:
        logger.error("sync_all_users_failed", error=str(e))


def start_scheduler():
    """
    Initialize and start the APScheduler for periodic email synchronization.
    
    Configures the scheduler to run sync_all_users() every 15 minutes.
    This function should be called on application startup.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    
    logger.info("scheduler_starting")
    
    scheduler = AsyncIOScheduler()
    
    # Add sync job with 15-minute interval
    scheduler.add_job(
        sync_all_users,
        trigger=IntervalTrigger(minutes=15),
        id='sync_all_users',
        name='Sync all users emails',
        replace_existing=True
    )
    
    scheduler.start()
    
    logger.info("scheduler_started", interval_minutes=15)
    
    return scheduler
