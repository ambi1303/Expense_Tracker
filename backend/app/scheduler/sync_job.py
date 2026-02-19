"""
Sync job for automated email synchronization.

This module implements the background job that periodically fetches and processes
Gmail emails for all active users, extracting transaction data and storing it
in the database.
"""

from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.sync_log import SyncLog
from app.auth.encryption import decrypt_refresh_token
from app.auth.oauth import refresh_access_token
from app.services.gmail_service import fetch_transaction_emails, get_email_content
from app.services.email_parser import parse_email
from app.services.transaction_service import create_transaction, get_processed_message_ids


logger = structlog.get_logger()


async def sync_user_emails(user: User, session: AsyncSession) -> dict:
    """
    Sync emails for a single user.
    
    Fetches new transaction emails from Gmail, parses them, and stores
    transactions in the database. Handles token refresh and duplicate filtering.
    
    Args:
        user: User object to sync emails for.
        session: Database session.
        
    Returns:
        Dict with sync results: {
            'success': bool,
            'emails_processed': int,
            'transactions_created': int,
            'error': str or None
        }
    """
    logger.info("sync_user_emails_started", user_id=str(user.id), email=user.email)
    
    try:
        # Decrypt and refresh access token
        refresh_token = decrypt_refresh_token(user.refresh_token_encrypted)
        access_token = refresh_access_token(refresh_token)  # Not async
        
        logger.info("access_token_refreshed", user_id=str(user.id))
        
        # Fetch new emails from Gmail
        emails = await fetch_transaction_emails(access_token)
        
        logger.info(
            "emails_fetched",
            user_id=str(user.id),
            email_count=len(emails)
        )
        
        # Get already processed message IDs
        processed_ids = await get_processed_message_ids(session, user.id)
        
        # Filter out already processed emails
        new_emails = [e for e in emails if e['message_id'] not in processed_ids]
        
        logger.info(
            "emails_filtered",
            user_id=str(user.id),
            new_emails=len(new_emails),
            already_processed=len(emails) - len(new_emails)
        )
        
        # Process each new email
        transactions_created = 0
        emails_processed = 0
        
        for email in new_emails:
            try:
                # Get full email content
                email_content = await get_email_content(
                    access_token,
                    email['message_id']
                )
                
                # Parse email to extract transaction data
                parsed = parse_email(
                    email_content.get('subject', ''),
                    email_content.get('body', '')
                )
                
                if parsed:
                    # Create transaction in database
                    transaction = await create_transaction(
                        db=session,
                        user_id=user.id,
                        parsed_transaction=parsed,
                        message_id=email['message_id']
                    )
                    
                    if transaction:
                        transactions_created += 1
                        logger.info(
                            "transaction_created",
                            user_id=str(user.id),
                            transaction_id=str(transaction.id),
                            message_id=email['message_id']
                        )
                    else:
                        logger.warning(
                            "transaction_duplicate_skipped",
                            user_id=str(user.id),
                            message_id=email['message_id']
                        )
                else:
                    logger.warning(
                        "email_parse_failed",
                        user_id=str(user.id),
                        message_id=email['message_id']
                    )
                
                emails_processed += 1
                
            except Exception as e:
                logger.error(
                    "email_processing_error",
                    user_id=str(user.id),
                    message_id=email.get('message_id'),
                    error=str(e)
                )
                # Continue processing other emails
                continue
        
        logger.info(
            "sync_user_emails_success",
            user_id=str(user.id),
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
            user_id=str(user.id),
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
    
    # Create a new database session for this job
    async with AsyncSessionLocal() as session:
        try:
            # Fetch all users
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            logger.info("users_fetched", user_count=len(users))
            
            total_processed = 0
            total_errors = 0
            
            # Process each user
            for user in users:
                try:
                    # Sync user emails
                    sync_result = await sync_user_emails(user, session)
                    
                    # Create sync log entry
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
                    # Log error but continue with other users
                    logger.error(
                        "user_sync_error",
                        user_id=str(user.id),
                        error=str(e)
                    )
                    
                    # Try to create error log entry
                    try:
                        sync_log = SyncLog(
                            user_id=user.id,
                            status="failed",
                            emails_processed=0,
                            errors=str(e)
                        )
                        session.add(sync_log)
                        await session.commit()
                    except Exception as log_error:
                        logger.error(
                            "sync_log_creation_failed",
                            user_id=str(user.id),
                            error=str(log_error)
                        )
                    
                    total_errors += 1
                    # Continue with next user
                    continue
            
            logger.info(
                "sync_all_users_completed",
                total_users=len(users),
                successful=total_processed,
                failed=total_errors
            )
            
        except Exception as e:
            logger.error(
                "sync_all_users_failed",
                error=str(e)
            )
        finally:
            # Ensure session is closed
            await session.close()


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
