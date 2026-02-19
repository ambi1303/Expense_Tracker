"""
Email parser for extracting transaction details from bank emails.

This module provides functions to parse transaction emails from Indian banks
and extract structured transaction data including amount, type, merchant, date, and bank.
"""

import re
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel
from enum import Enum
import structlog


logger = structlog.get_logger()


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"


class ParsedTransaction(BaseModel):
    """Structured transaction data extracted from email."""
    amount: Decimal
    currency: str = "INR"
    transaction_type: TransactionType
    merchant: Optional[str] = None
    transaction_date: datetime
    bank_name: Optional[str] = None


# Regex patterns for extracting transaction details from Indian bank emails
AMOUNT_PATTERNS = [
    r'(?:INR|Rs\.?)\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:amount|Amount|AMOUNT):\s*(?:INR|Rs\.?)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:debited|credited)\s+(?:with\s+)?(?:INR|Rs\.?)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
]

DEBIT_KEYWORDS = ['debited', 'debit', 'spent', 'withdrawn', 'paid', 'purchase']
CREDIT_KEYWORDS = ['credited', 'credit', 'received', 'deposited', 'refund']

MERCHANT_PATTERNS = [
    r'(?:at|to|from)\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+dated|\s+for)',
    r'(?:merchant|Merchant|MERCHANT):\s*([A-Za-z0-9\s&\-\.]+)',
    r'(?:paid to|Paid to|PAID TO)\s+([A-Za-z0-9\s&\-\.]+)',
]

DATE_PATTERNS = [
    r'(\d{2}-\d{2}-\d{4})',  # DD-MM-YYYY
    r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
    r'on\s+(\d{2}\s+[A-Za-z]+\s+\d{4})',  # on DD Month YYYY
    r'(\d{2}\s+[A-Za-z]{3}\s+\d{4})',  # DD Mon YYYY
]

BANK_PATTERNS = {
    'HDFC': ['hdfc', 'hdfcbank'],
    'ICICI': ['icici', 'icicibank'],
    'SBI': ['sbi', 'state bank'],
    'Axis': ['axis', 'axisbank'],
    'Kotak': ['kotak', 'kotakbank'],
    'IDFC': ['idfc', 'idfcbank'],
    'Yes Bank': ['yesbank', 'yes bank'],
    'IndusInd': ['indusind'],
}


def parse_email(subject: str, body: str) -> Optional[ParsedTransaction]:
    """
    Parse email content to extract transaction details.
    
    Args:
        subject: Email subject line.
        body: Email body content.
        
    Returns:
        ParsedTransaction object if parsing succeeds, None otherwise.
    """
    logger.info("parse_email_started")
    
    try:
        # Combine subject and body for parsing
        text = f"{subject}\n{body}"
        
        # Extract required fields
        amount = extract_amount(text)
        transaction_type = extract_transaction_type(text)
        transaction_date = extract_date(text)
        
        # Check if all required fields are present
        if not amount or not transaction_type or not transaction_date:
            logger.warning(
                "parse_email_incomplete",
                has_amount=bool(amount),
                has_type=bool(transaction_type),
                has_date=bool(transaction_date)
            )
            return None
        
        # Extract optional fields
        merchant = extract_merchant(text)
        bank_name = extract_bank(text)
        
        # Create parsed transaction
        parsed = ParsedTransaction(
            amount=amount,
            currency="INR",
            transaction_type=transaction_type,
            merchant=merchant,
            transaction_date=transaction_date,
            bank_name=bank_name
        )
        
        logger.info("parse_email_success", amount=str(amount), type=transaction_type)
        
        return parsed
        
    except Exception as e:
        logger.error("parse_email_failed", error=str(e))
        return None


def extract_amount(text: str) -> Optional[Decimal]:
    """
    Extract transaction amount from text using regex patterns.
    
    Args:
        text: Text to extract amount from.
        
    Returns:
        Decimal amount if found, None otherwise.
    """
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the amount string and remove commas
            amount_str = match.group(1).replace(',', '')
            try:
                return Decimal(amount_str)
            except Exception:
                continue
    
    return None


def extract_transaction_type(text: str) -> Optional[TransactionType]:
    """
    Identify whether transaction is debit or credit.
    
    Uses word boundary matching and counts occurrences to avoid
    false positives from substring matches.
    
    Args:
        text: Text to analyze.
        
    Returns:
        TransactionType if identified, None otherwise.
    """
    import re
    
    text_lower = text.lower()
    
    # Use word boundaries to avoid substring matches like "discredited"
    debit_pattern = r'\b(?:' + '|'.join(DEBIT_KEYWORDS) + r')\b'
    credit_pattern = r'\b(?:' + '|'.join(CREDIT_KEYWORDS) + r')\b'
    
    # Count matches for each type
    debit_matches = len(re.findall(debit_pattern, text_lower))
    credit_matches = len(re.findall(credit_pattern, text_lower))
    
    # Return the type with more matches
    if debit_matches > credit_matches:
        return TransactionType.DEBIT
    elif credit_matches > debit_matches:
        return TransactionType.CREDIT
    
    # If equal or both zero, return None
    return None


def extract_merchant(text: str) -> Optional[str]:
    """
    Extract merchant name from text using regex patterns.
    
    Args:
        text: Text to extract merchant from.
        
    Returns:
        Merchant name if found, None otherwise.
    """
    for pattern in MERCHANT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            merchant = match.group(1).strip()
            # Clean up merchant name
            merchant = re.sub(r'\s+', ' ', merchant)  # Remove extra spaces
            if len(merchant) > 3:  # Minimum length check
                return merchant
    
    return None


def extract_date(text: str) -> Optional[datetime]:
    """
    Extract transaction date from text using regex patterns.
    
    Args:
        text: Text to extract date from.
        
    Returns:
        datetime object if found, None otherwise.
    """
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            
            # Try different date formats
            date_formats = [
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%d %B %Y',
                '%d %b %Y',
            ]
            
            for fmt in date_formats:
                try:
                    # Parse date and make it timezone-aware (UTC)
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Add UTC timezone
                    from datetime import timezone
                    return parsed_date.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    
    # If no date found in text, return None instead of fallback
    # This will cause parse_email to return None, properly rejecting the email
    return None


def extract_bank(text: str) -> Optional[str]:
    """
    Identify bank name from email content.
    
    Args:
        text: Text to analyze (typically email sender or body).
        
    Returns:
        Bank name if identified, None otherwise.
    """
    text_lower = text.lower()
    
    for bank_name, keywords in BANK_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return bank_name
    
    return None
