"""
Gmail API service for fetching transaction emails.

This module provides functions to interact with the Gmail API to fetch
transaction-related emails using search queries and retrieve email content.
"""

from typing import List, Dict, Optional
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
import base64
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor


logger = structlog.get_logger()

# Thread pool executor for async Gmail API calls
_executor = ThreadPoolExecutor(max_workers=10)


# Search query for transaction emails (content keywords)
TRANSACTION_SEARCH_QUERY = '("INR" OR "Rs" OR "debited" OR "credited")'

# Sender domains to narrow search (opt-in via GMAIL_BANK_DOMAINS env)
# Format: comma-separated, e.g. "hdfcbank.com,icicibank.com,sbi.co.in"
# If unset or empty, no sender filter (broader search, more results)
_bank_domains_env = os.getenv("GMAIL_BANK_DOMAINS", "")
BANK_SENDER_DOMAINS = [d.strip().lower() for d in _bank_domains_env.split(",") if d.strip()]

# Max concurrent fetches for email content (avoid rate limits)
MAX_CONCURRENT_FETCHES = int(os.getenv("GMAIL_MAX_CONCURRENT_FETCHES", "10"))

# Retries for individual email fetch failures
FETCH_CONTENT_RETRIES = int(os.getenv("GMAIL_FETCH_RETRIES", "3"))


def _build_search_query(last_sync_time: Optional[datetime], is_first_sync: bool) -> str:
    """
    Build Gmail search query with optional date filter and sender filter.
    Uses Unix timestamp for 'after:' to avoid timezone ambiguity (Gmail uses PST for YYYY/MM/DD).
    """
    parts = [TRANSACTION_SEARCH_QUERY]
    
    # Date filter: use Unix timestamp for precise timezone-agnostic filtering
    if last_sync_time:
        ts = int(last_sync_time.timestamp())
        parts.append(f"after:{ts}")
    
    # Sender filter: narrow to known bank domains when configured
    if BANK_SENDER_DOMAINS:
        from_query = " OR ".join(f"from:{d}" for d in BANK_SENDER_DOMAINS)
        parts.append(f"({from_query})")
    
    return " ".join(parts)


def get_gmail_service(access_token: str):
    """
    Create a Gmail API service instance.
    
    Args:
        access_token: Valid OAuth access token.
        
    Returns:
        Gmail API service instance.
        
    Raises:
        ValueError: If access token is invalid.
    """
    if not access_token:
        raise ValueError("Access token cannot be empty")
    
    # Create credentials from access token
    credentials = Credentials(token=access_token)
    
    # Build Gmail service
    service = build('gmail', 'v1', credentials=credentials)
    
    return service


# First sync: fetch up to this many emails (full backfill)
FIRST_SYNC_MAX_RESULTS = int(os.getenv("GMAIL_FIRST_SYNC_MAX", "10000"))

# Incremental sync: cap per run to avoid long syncs
INCREMENTAL_SYNC_MAX_RESULTS = int(os.getenv("GMAIL_INCREMENTAL_SYNC_MAX", "500"))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
async def fetch_transaction_emails(
    access_token: str,
    last_sync_time: Optional[datetime] = None,
    max_results: Optional[int] = None
) -> List[Dict[str, any]]:
    """
    Fetch transaction-related emails from Gmail with pagination support.
    
    - First sync (last_sync_time=None): Fetches up to FIRST_SYNC_MAX_RESULTS,
      paginating through all pages to import historical data.
    - Incremental sync: Fetches emails after last_sync_time, capped at
      INCREMENTAL_SYNC_MAX_RESULTS.
    
    Uses Unix timestamp for date filter to avoid timezone issues.
    Fetches email content in parallel with bounded concurrency and per-message retries.
    
    Args:
        access_token: Valid OAuth access token for Gmail API.
        last_sync_time: Optional datetime to fetch emails after this time.
        max_results: Override max results (default: auto based on first vs incremental).
        
    Returns:
        List of dictionaries containing message_id, subject, body, and date.
    """
    is_first_sync = last_sync_time is None
    effective_max = max_results or (
        FIRST_SYNC_MAX_RESULTS if is_first_sync else INCREMENTAL_SYNC_MAX_RESULTS
    )
    
    logger.info("fetch_transaction_emails_started",
               last_sync_time=last_sync_time,
               is_first_sync=is_first_sync,
               max_results=effective_max)
    
    try:
        loop = asyncio.get_event_loop()
        
        def _fetch_message_ids_sync():
            """Synchronous function to fetch message IDs with pagination."""
            service = get_gmail_service(access_token)
            query = _build_search_query(last_sync_time, is_first_sync)
            
            logger.info("gmail_api_search", query=query)
            
            all_messages = []
            next_page_token = None
            
            while len(all_messages) < effective_max:
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(100, effective_max - len(all_messages)),
                    pageToken=next_page_token
                ).execute()
                
                messages = results.get('messages', [])
                all_messages.extend(messages)
                
                logger.info("gmail_api_page_fetched",
                           page_count=len(messages),
                           total_count=len(all_messages))
                
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info("gmail_api_search_complete", message_count=len(all_messages))
            return all_messages
        
        all_messages = await loop.run_in_executor(_executor, _fetch_message_ids_sync)
        
        # Fetch full content in parallel with bounded concurrency
        sem = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
        
        async def _fetch_with_retry(msg: dict) -> Optional[Dict]:
            message_id = msg['id']
            last_error = None
            for attempt in range(FETCH_CONTENT_RETRIES):
                try:
                    async with sem:
                        return await get_email_content(access_token, message_id)
                except Exception as e:
                    last_error = e
                    if attempt < FETCH_CONTENT_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)  # Backoff
                    else:
                        logger.error(
                            "failed_to_fetch_email_content",
                            message_id=message_id,
                            error=str(e),
                            attempts=FETCH_CONTENT_RETRIES
                        )
            return None
        
        tasks = [_fetch_with_retry(m) for m in all_messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        emails = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(
                    "fetch_task_exception",
                    message_id=all_messages[i]['id'],
                    error=str(r)
                )
            elif r is not None:
                emails.append(r)
        
        logger.info("fetch_transaction_emails_complete", emails_fetched=len(emails))
        return emails
        
    except HttpError as e:
        logger.error("gmail_api_error", error=str(e), status_code=e.resp.status)
        raise
    except Exception as e:
        logger.error("fetch_transaction_emails_failed", error=str(e))
        raise ValueError(f"Failed to fetch emails: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
async def get_email_content(access_token: str, message_id: str) -> Dict[str, any]:
    """
    Fetch full email content for a specific message ID asynchronously.
    
    Uses ThreadPoolExecutor to avoid blocking the event loop with synchronous
    Gmail API calls.
    
    This function includes retry logic with exponential backoff for handling
    transient Gmail API errors.
    
    Args:
        access_token: Valid OAuth access token for Gmail API.
        message_id: Gmail message ID to fetch.
        
    Returns:
        Dictionary containing message_id, subject, body, and date.
        
    Raises:
        ValueError: If access token or message_id is invalid.
        HttpError: If Gmail API request fails after retries.
    """
    if not message_id:
        raise ValueError("Message ID cannot be empty")
    
    logger.info("get_email_content_started", message_id=message_id)
    
    try:
        # Wrap synchronous Gmail API call in executor
        loop = asyncio.get_event_loop()
        
        def _get_email_sync():
            """Synchronous function to fetch email content."""
            service = get_gmail_service(access_token)
            
            # Fetch message
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            
            # Extract body
            body = _extract_body(message.get('payload', {}))
            
            # Parse date
            email_date = None
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(date_str)
                except Exception as e:
                    logger.warning("failed_to_parse_email_date", date_str=date_str, error=str(e))
            
            return {
                'message_id': message_id,
                'subject': subject,
                'body': body,
                'date': email_date
            }
        
        # Execute synchronous fetch in thread pool
        email_data = await loop.run_in_executor(_executor, _get_email_sync)
        
        logger.info("get_email_content_complete", message_id=message_id)
        
        return email_data
        
    except HttpError as e:
        logger.error(
            "gmail_api_error_get_message",
            message_id=message_id,
            error=str(e),
            status_code=e.resp.status
        )
        raise
    except Exception as e:
        logger.error("get_email_content_failed", message_id=message_id, error=str(e))
        raise ValueError(f"Failed to get email content: {str(e)}")


def _extract_body(payload: Dict) -> str:
    """
    Extract email body from Gmail message payload.
    
    Handles both plain text and multipart messages.
    Prioritizes text/plain over text/html for cleaner parsing.
    Strips HTML tags from HTML parts when plain text is not available.
    
    Args:
        payload: Gmail message payload.
        
    Returns:
        Email body as string.
    """
    plain_text_parts = []
    html_parts = []
    
    def _collect_parts(payload_part):
        """Recursively collect text parts."""
        mime_type = payload_part.get('mimeType', '')
        
        # Extract body data
        if 'body' in payload_part and 'data' in payload_part['body']:
            body_data = payload_part['body']['data']
            body_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
            
            if 'text/plain' in mime_type:
                plain_text_parts.append(body_text)
            elif 'text/html' in mime_type:
                html_parts.append(body_text)
        
        # Recurse into parts
        if 'parts' in payload_part:
            for part in payload_part['parts']:
                _collect_parts(part)
    
    _collect_parts(payload)
    
    # Prefer plain text over HTML
    if plain_text_parts:
        return '\n'.join(plain_text_parts).strip()
    elif html_parts:
        # Strip HTML tags from HTML parts using BeautifulSoup
        from app.services.email_parser import _strip_html
        return '\n'.join(_strip_html(html) for html in html_parts).strip()
    else:
        return ""
