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


# Search query for transaction emails
TRANSACTION_SEARCH_QUERY = '("INR" OR "Rs" OR "debited" OR "credited")'


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
async def fetch_transaction_emails(
    access_token: str,
    last_sync_time: Optional[datetime] = None,
    max_results: int = 500
) -> List[Dict[str, any]]:
    """
    Fetch transaction-related emails from Gmail with pagination support.
    
    Uses the search query: ("INR" OR "Rs" OR "debited" OR "credited")
    to find emails that likely contain transaction information.
    
    Implements nextPageToken pagination to fetch all emails beyond the 100-message limit.
    Uses async execution with ThreadPoolExecutor to avoid blocking the event loop.
    
    This function includes retry logic with exponential backoff for handling
    transient Gmail API errors.
    
    Args:
        access_token: Valid OAuth access token for Gmail API.
        last_sync_time: Optional datetime to fetch emails after this time.
        max_results: Maximum number of emails to fetch (default 500).
        
    Returns:
        List of dictionaries containing message_id, subject, body, and date.
        
    Raises:
        ValueError: If access token is invalid.
        HttpError: If Gmail API request fails after retries.
    """
    logger.info("fetch_transaction_emails_started", 
               last_sync_time=last_sync_time,
               max_results=max_results)
    
    try:
        # Wrap synchronous Gmail API calls in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        
        def _fetch_message_ids_sync():
            """Synchronous function to fetch message IDs with pagination."""
            service = get_gmail_service(access_token)
            
            # Build search query
            query = TRANSACTION_SEARCH_QUERY
            
            # Add date filter if last_sync_time is provided
            if last_sync_time:
                # Format: after:YYYY/MM/DD
                date_str = last_sync_time.strftime("%Y/%m/%d")
                query += f" after:{date_str}"
            
            logger.info("gmail_api_search", query=query)
            
            # Pagination loop to fetch all messages
            all_messages = []
            next_page_token = None
            
            while len(all_messages) < max_results:
                # Fetch page
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(100, max_results - len(all_messages)),
                    pageToken=next_page_token
                ).execute()
                
                messages = results.get('messages', [])
                all_messages.extend(messages)
                
                logger.info("gmail_api_page_fetched",
                           page_count=len(messages),
                           total_count=len(all_messages))
                
                # Check for next page
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break  # No more pages
            
            logger.info("gmail_api_search_complete", message_count=len(all_messages))
            return all_messages
        
        # Execute synchronous fetch in thread pool
        all_messages = await loop.run_in_executor(_executor, _fetch_message_ids_sync)
        
        # Fetch full content for each message (asynchronously)
        emails = []
        for message in all_messages:
            message_id = message['id']
            
            try:
                email_data = await get_email_content(access_token, message_id)
                emails.append(email_data)
            except Exception as e:
                logger.error(
                    "failed_to_fetch_email_content",
                    message_id=message_id,
                    error=str(e)
                )
                # Continue with other emails
                continue
        
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
