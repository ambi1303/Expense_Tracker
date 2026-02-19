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


logger = structlog.get_logger()


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
    last_sync_time: Optional[datetime] = None
) -> List[Dict[str, any]]:
    """
    Fetch transaction-related emails from Gmail.
    
    Uses the search query: ("INR" OR "Rs" OR "debited" OR "credited")
    to find emails that likely contain transaction information.
    
    This function includes retry logic with exponential backoff for handling
    transient Gmail API errors.
    
    Args:
        access_token: Valid OAuth access token for Gmail API.
        last_sync_time: Optional datetime to fetch emails after this time.
        
    Returns:
        List of dictionaries containing message_id, subject, body, and date.
        
    Raises:
        ValueError: If access token is invalid.
        HttpError: If Gmail API request fails after retries.
    """
    logger.info("fetch_transaction_emails_started", last_sync_time=last_sync_time)
    
    try:
        # Create Gmail service
        service = get_gmail_service(access_token)
        
        # Build search query
        query = TRANSACTION_SEARCH_QUERY
        
        # Add date filter if last_sync_time is provided
        if last_sync_time:
            # Format: after:YYYY/MM/DD
            date_str = last_sync_time.strftime("%Y/%m/%d")
            query += f" after:{date_str}"
        
        logger.info("gmail_api_search", query=query)
        
        # Search for messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=100  # Fetch up to 100 messages per request
        ).execute()
        
        messages = results.get('messages', [])
        
        logger.info("gmail_api_search_complete", message_count=len(messages))
        
        # Fetch full content for each message
        emails = []
        for message in messages:
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
    Fetch full email content for a specific message ID.
    
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
        # Create Gmail service
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
        
        logger.info("get_email_content_complete", message_id=message_id)
        
        return {
            'message_id': message_id,
            'subject': subject,
            'body': body,
            'date': email_date
        }
        
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
    
    Args:
        payload: Gmail message payload.
        
    Returns:
        Email body as string.
    """
    body = ""
    
    # Check if payload has body data
    if 'body' in payload and 'data' in payload['body']:
        body_data = payload['body']['data']
        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
    
    # Check for parts (multipart message)
    elif 'parts' in payload:
        for part in payload['parts']:
            # Recursively extract body from parts
            part_body = _extract_body(part)
            if part_body:
                body += part_body + "\n"
    
    return body.strip()
