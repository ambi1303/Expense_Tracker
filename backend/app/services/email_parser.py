"""
Email parser for extracting transaction details from bank emails.

This module provides functions to parse transaction emails from Indian banks
and extract structured transaction data including amount, type, merchant, date, and bank.
"""

import re
from typing import Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pydantic import BaseModel
from enum import Enum
import structlog
import html
from bs4 import BeautifulSoup


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
    category: Optional[str] = None
    payment_method: Optional[str] = None
    upi_reference: Optional[str] = None
    raw_snippet: Optional[str] = None


# Regex patterns for extracting transaction details from Indian bank emails
# Updated to include Unicode ₹ symbol
AMOUNT_PATTERNS = [
    r'(?:INR|Rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:amount|Amount|AMOUNT):\s*(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:debited|credited)\s+(?:with\s+)?(?:INR|Rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:INR|Rs\.?|₹)(\d+(?:,\d+)*(?:\.\d{2})?)',  # More flexible - just currency + amount
]

DEBIT_KEYWORDS = ['debited', 'debit', 'spent', 'withdrawn', 'paid', 'purchase']
CREDIT_KEYWORDS = ['credited', 'credit', 'received', 'deposited', 'refund']

MERCHANT_PATTERNS = [
    r'(?:at|to|from)\s+([A-Za-z0-9][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+dated|\s+for)',  # Allow lowercase start
    r'(?:merchant|Merchant|MERCHANT):\s*([A-Za-z0-9\s&\-\.]+)',
    r'(?:paid to|Paid to|PAID TO)\s+([A-Za-z0-9\s&\-\.]+)',
]

DATE_PATTERNS = [
    r'(\d{1,2}-\d{1,2}-\d{4})',  # DD-MM-YYYY or D-M-YYYY (single digit support)
    r'(\d{1,2}/\d{1,2}/\d{4})',  # DD/MM/YYYY or D/M/YYYY (single digit support)
    r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD (ISO format)
    r'on\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})',  # on DD Month YYYY
    r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',  # DD Mon/Month YYYY (3-9 chars for month)
    r'dated\s+(\d{1,2}-\d{1,2}-\d{4})',  # dated DD-MM-YYYY
    r'dated\s+(\d{1,2}/\d{1,2}/\d{4})',  # dated DD/MM/YYYY
    r'(\d{1,2}-[A-Za-z]{3}-\d{4})',  # DD-Mon-YYYY
]

# Keywords that indicate non-transaction emails (should be rejected)
NON_TRANSACTION_KEYWORDS = [
    r'\bOTP\b',
    r'\bone.time.password\b',
    r'\bverification.code\b',
    r'\bstatement\s+(?:is\s+)?available\b',
    r'\bmonthly\s+statement\b',
    r'\bdownload\s+statement\b',
    r'\bview\s+statement\b',
    r'\bpassword\s+reset\b',
    r'\bactivate\s+card\b',
    r'\bcard\s+activation\b',
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
    'Paytm': ['paytm'],
    'AU Bank': ['au bank', 'au small finance'],
    'RBL': ['rbl', 'rbl bank'],
    'Federal': ['federal', 'federal bank'],
    'Bank of Baroda': ['bank of baroda', 'bob'],
    'Canara': ['canara', 'canara bank'],
    'PNB': ['pnb', 'punjab national'],
}

# UPI patterns for Indian payment systems
UPI_PATTERNS = [
    r'UPI\s*(?:Ref|Reference|ID|Transaction)[\s:]*([A-Za-z0-9]{12,})',
    r'UPI\s*(?:Txn|Trans)[\s:]*([A-Za-z0-9]{12,})',
    r'(?:Ref|Reference)\s*(?:No|Number)?[\s:]*([A-Za-z0-9]{12,})',
]

# Payment method keywords
PAYMENT_METHOD_KEYWORDS = {
    'UPI': ['upi', 'paytm', 'phonepe', 'googlepay', 'gpay', 'bhim'],
    'Card': ['card', 'debit card', 'credit card', 'visa', 'mastercard', 'rupay'],
    'NetBanking': ['netbanking', 'net banking', 'online banking', 'internet banking'],
    'Wallet': ['wallet', 'paytm wallet', 'phonepe wallet'],
    'Cash': ['cash', 'atm withdrawal', 'atm'],
}

# Category keyword mappings for auto-categorization
CATEGORY_KEYWORDS = {
    'Food': [
        'swiggy', 'zomato', 'uber eats', 'dominos', 'pizza', 'restaurant',
        'cafe', 'food', 'mcdonald', 'kfc', 'subway', 'starbucks'
    ],
    'Groceries': [
        'bigbasket', 'grofers', 'blinkit', 'dunzo', 'dmart', 'reliance fresh',
        'more', 'supermarket', 'grocery', 'vegetables', 'fruits'
    ],
    'Shopping': [
        'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'shopping',
        'mall', 'store', 'retail'
    ],
    'Transport': [
        'uber', 'ola', 'rapido', 'metro', 'bus', 'taxi', 'fuel',
        'petrol', 'diesel', 'parking', 'toll'
    ],
    'Bills': [
        'electricity', 'water', 'gas', 'internet', 'broadband', 'mobile',
        'recharge', 'bill payment', 'utility'
    ],
    'Entertainment': [
        'netflix', 'amazon prime', 'hotstar', 'spotify', 'movie', 'cinema',
        'theatre', 'gaming', 'subscription'
    ],
    'Healthcare': [
        'pharmacy', 'hospital', 'clinic', 'doctor', 'medicine', 'medical',
        'health', 'apollo', 'medplus'
    ],
    'Education': [
        'school', 'college', 'university', 'course', 'tuition', 'books',
        'education', 'learning'
    ],
}


def _strip_html(text: str) -> str:
    """
    Strip HTML tags and decode HTML entities from text using BeautifulSoup.
    
    Uses BeautifulSoup for robust HTML parsing and tag removal, handling
    complex HTML structures, nested tags, and HTML entities.
    
    Args:
        text: Text that may contain HTML.
        
    Returns:
        Plain text with HTML removed.
    """
    # Decode HTML entities first (e.g., &nbsp; -> space, &amp; -> &)
    text = html.unescape(text)
    
    # Use BeautifulSoup to strip HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def _is_non_transaction_email(text: str) -> bool:
    """
    Check if email is a non-transaction email (OTP, statement, etc.).
    
    Args:
        text: Combined subject and body text.
        
    Returns:
        True if email should be rejected, False otherwise.
    """
    text_lower = text.lower()
    
    for pattern in NON_TRANSACTION_KEYWORDS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.info("non_transaction_email_detected", pattern=pattern)
            return True
    
    return False


def extract_upi_reference(text: str) -> Optional[str]:
    """
    Extract UPI reference ID from text.
    
    Args:
        text: Text to extract UPI reference from.
        
    Returns:
        UPI reference ID if found, None otherwise.
    """
    for pattern in UPI_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            upi_ref = match.group(1).strip()
            # Validate length (UPI refs are typically 12+ chars)
            if len(upi_ref) >= 12:
                logger.debug("upi_reference_extracted", upi_ref=upi_ref)
                return upi_ref
    return None


def extract_payment_method(text: str) -> Optional[str]:
    """
    Identify payment method from text.
    
    Args:
        text: Text to analyze.
        
    Returns:
        Payment method if identified, None otherwise.
    """
    text_lower = text.lower()
    
    for method, keywords in PAYMENT_METHOD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                logger.debug("payment_method_extracted", method=method)
                return method
    
    return None


def fuzzy_match(text: str, keyword: str, threshold: float = 0.8) -> bool:
    """
    Check if text fuzzy matches keyword using SequenceMatcher.
    
    Args:
        text: Text to match.
        keyword: Keyword to match against.
        threshold: Similarity threshold (0.0 to 1.0).
        
    Returns:
        True if similarity >= threshold, False otherwise.
    """
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, text.lower(), keyword.lower()).ratio()
    return ratio >= threshold


def auto_categorize(merchant: Optional[str], text: str) -> Optional[str]:
    """
    Auto-categorize transaction based on merchant and text.
    
    Uses exact keyword matching and fuzzy matching on merchant name
    to assign category.
    
    Args:
        merchant: Merchant name (optional).
        text: Full email text.
        
    Returns:
        Category name if matched, None otherwise.
    """
    if not merchant and not text:
        return None
    
    search_text = f"{merchant or ''} {text}".lower()
    
    # Exact keyword matching
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in search_text:
                logger.debug("category_matched_exact",
                           category=category, keyword=keyword)
                return category
    
    # Fuzzy matching on merchant name
    if merchant:
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if fuzzy_match(merchant, keyword, threshold=0.75):
                    logger.debug("category_matched_fuzzy",
                               category=category, keyword=keyword)
                    return category
    
    return None


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
        # Strip HTML tags from both subject and body
        subject = _strip_html(subject)
        body = _strip_html(body)
        
        # Combine subject and body for parsing
        text = f"{subject}\n{body}"
        
        # Pre-filter: Reject non-transaction emails
        if _is_non_transaction_email(text):
            logger.info("parse_email_rejected_non_transaction")
            return None
        
        # Pre-filter: Must contain currency pattern (including ₹ Unicode symbol)
        if not re.search(r'\b(?:INR|Rs\.?|₹)\b', text, re.IGNORECASE):
            logger.info("parse_email_rejected_no_currency")
            return None
        
        # Pre-filter: Must contain debit/credit keyword
        if not re.search(r'\b(?:debit|credit)(?:ed)?\b', text, re.IGNORECASE):
            logger.info("parse_email_rejected_no_transaction_keyword")
            return None
        
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
        
        # Extract new fields
        upi_reference = extract_upi_reference(text)
        payment_method = extract_payment_method(text)
        
        # Create raw snippet (first 500 chars)
        raw_snippet = text[:500] if len(text) > 500 else text
        
        # Auto-categorize
        category = auto_categorize(merchant, text)
        
        # Create parsed transaction
        parsed = ParsedTransaction(
            amount=amount,
            currency="INR",
            transaction_type=transaction_type,
            merchant=merchant,
            transaction_date=transaction_date,
            bank_name=bank_name,
            category=category,
            payment_method=payment_method,
            upi_reference=upi_reference,
            raw_snippet=raw_snippet
        )
        
        logger.info("parse_email_success", amount=str(amount), type=transaction_type)
        
        return parsed
        
    except (ValueError, TypeError) as e:
        logger.error("parse_email_failed", error=str(e), error_type=type(e).__name__)
        return None
    except Exception as e:
        # Re-raise unexpected exceptions for debugging
        logger.error("parse_email_unexpected_error", error=str(e), error_type=type(e).__name__)
        raise


def extract_amount(text: str) -> Optional[Decimal]:
    """
    Extract transaction amount from text using regex patterns.
    
    Handles multiple amounts by:
    1. Collecting all amounts found
    2. Looking for contextual keywords near amounts
    3. Returning amount closest to transaction keyword
    4. Falling back to smallest amount if no contextual match (conservative approach)
    
    Args:
        text: Text to extract amount from.
        
    Returns:
        Decimal amount if found, None otherwise.
    """
    amounts_with_context = []
    
    # Keywords that indicate the actual transaction amount (STRONG indicators)
    strong_transaction_keywords = [
        'debited', 'credited', 'paid', 'withdrawn', 'received',
        'purchase', 'transaction', 'final', 'total', 'charged'
    ]
    
    # Keywords that indicate amounts to SKIP (only if no strong keyword nearby)
    skip_keywords = [
        'available balance', 'current balance', 'balance:', 'balance is',
        'discount applied', 'discount:', 'discount ', 'discount of',
        'cashback', 'reward', 'points', 
        'limit', 'minimum due', 'order total', 'order amount', 'order value',
        'order:', 'order '
    ]
    
    # Collect all amounts with their positions and context
    for pattern in AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = Decimal(amount_str)
                
                # Validate amount is positive and non-zero
                if amount <= 0:
                    logger.debug("amount_rejected_non_positive", amount=amount)
                    continue
                
                # Get context around the amount (80 chars before and after for better context)
                start_pos = max(0, match.start() - 80)
                end_pos = min(len(text), match.end() + 80)
                context = text[start_pos:end_pos].lower()
                
                # Check for strong transaction keywords (these override skip keywords)
                has_strong_keyword = any(kw in context for kw in strong_transaction_keywords)
                
                # Check for skip keywords
                has_skip_keyword = any(skip_kw in context for skip_kw in skip_keywords)
                
                # Skip only if has skip keyword AND no strong keyword
                if has_skip_keyword and not has_strong_keyword:
                    logger.debug("amount_skipped_context", amount=amount, reason="skip_keyword_no_strong")
                    continue
                
                amounts_with_context.append({
                    'amount': amount,
                    'position': match.start(),
                    'context': context,
                    'has_strong_keyword': has_strong_keyword
                })
            except (ValueError, TypeError, ArithmeticError) as e:
                logger.debug("amount_parse_error", amount_str=amount_str, error=str(e))
                continue
    
    if not amounts_with_context:
        return None
    
    # Strategy 1: Prioritize amounts with strong transaction keywords
    strong_amounts = [amt for amt in amounts_with_context if amt['has_strong_keyword']]
    if strong_amounts:
        # If multiple strong amounts, take the smallest one (conservative, likely the actual charge)
        # This handles cases like "Order Rs 1200 Final Rs 1000 debited"
        smallest_strong = min(strong_amounts, key=lambda x: x['amount'])
        logger.debug("amount_selected_strong_keyword", amount=smallest_strong['amount'])
        return smallest_strong['amount']
    
    # Strategy 2: Fallback to smallest amount (conservative approach)
    # This is safer than highest amount for financial accuracy
    smallest = min(amounts_with_context, key=lambda x: x['amount'])
    logger.debug("amount_selected_smallest", amount=smallest['amount'])
    return smallest['amount']


def extract_transaction_type(text: str) -> Optional[TransactionType]:
    """
    Identify whether transaction is debit or credit.
    
    Uses word boundary matching and counts occurrences to avoid
    false positives from substring matches. Prioritizes keywords
    that appear earlier in the text (likely in subject/first line).
    
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
    
    # Find all matches with their positions
    debit_matches = [(m.start(), m.group()) for m in re.finditer(debit_pattern, text_lower)]
    credit_matches = [(m.start(), m.group()) for m in re.finditer(credit_pattern, text_lower)]
    
    # If one type has significantly more matches, use that
    if len(debit_matches) > len(credit_matches) + 1:
        return TransactionType.DEBIT
    elif len(credit_matches) > len(debit_matches) + 1:
        return TransactionType.CREDIT
    
    # If counts are similar, prioritize the one that appears first
    # (subject line or early in email is more reliable)
    if debit_matches and credit_matches:
        first_debit_pos = debit_matches[0][0]
        first_credit_pos = credit_matches[0][0]
        
        if first_debit_pos < first_credit_pos:
            return TransactionType.DEBIT
        else:
            return TransactionType.CREDIT
    
    # If only one type found, return it
    if debit_matches:
        return TransactionType.DEBIT
    elif credit_matches:
        return TransactionType.CREDIT
    
    # If neither found, return None
    return None


def extract_merchant(text: str) -> Optional[str]:
    """
    Extract merchant name from text using regex patterns.
    
    Args:
        text: Text to extract merchant from.
        
    Returns:
        Merchant name if found and valid, None otherwise.
    """
    # Trailing noise words to remove
    noise_words = ['on', 'dated', 'for', 'ref', 'via', 'through', 'using']
    
    for pattern in MERCHANT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            merchant = match.group(1).strip()
            
            # Clean up merchant name
            merchant = re.sub(r'\s+', ' ', merchant)  # Remove extra spaces
            
            # Remove trailing noise words
            for noise in noise_words:
                if merchant.lower().endswith(f' {noise}'):
                    merchant = merchant[:-(len(noise) + 1)].strip()
            
            # Validate merchant length (min 3 chars, max 100 chars)
            if 3 <= len(merchant) <= 100:
                logger.debug("merchant_extracted", merchant=merchant)
                return merchant
            else:
                logger.debug("merchant_rejected_length", merchant=merchant, length=len(merchant))
    
    return None


def extract_date(text: str) -> Optional[datetime]:
    """
    Extract transaction date from text using regex patterns.
    
    Validates that dates are:
    - Not in the future (> now + 1 day)
    - Not older than 15 years
    - Valid calendar dates
    
    Args:
        text: Text to extract date from.
        
    Returns:
        Timezone-aware datetime object if found and valid, None otherwise.
    """
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            
            # Try different date formats
            date_formats = [
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%Y-%m-%d',  # ISO format
                '%d %B %Y',
                '%d %b %Y',
                '%d-%b-%Y',
                '%d-%B-%Y',
            ]
            
            for fmt in date_formats:
                try:
                    # Parse date
                    parsed_date = datetime.strptime(date_str, fmt)
                    
                    # Make timezone-aware (UTC)
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    
                    # Validation: Check date is not in the future
                    now = datetime.now(timezone.utc)
                    max_future_date = now + timedelta(days=1)
                    
                    if parsed_date > max_future_date:
                        logger.warning(
                            "date_rejected_future",
                            date=parsed_date.isoformat(),
                            now=now.isoformat()
                        )
                        continue
                    
                    # Validation: Check date is not too old (15 years)
                    min_past_date = now - timedelta(days=365 * 15)
                    
                    if parsed_date < min_past_date:
                        logger.warning(
                            "date_rejected_too_old",
                            date=parsed_date.isoformat(),
                            min_date=min_past_date.isoformat()
                        )
                        continue
                    
                    # Date is valid
                    logger.debug("date_extracted", date=parsed_date.isoformat())
                    return parsed_date
                    
                except ValueError:
                    # Invalid date format, try next format
                    continue
    
    # If no date found in text, return None instead of fallback
    # This will cause parse_email to return None, properly rejecting the email
    # Per Requirement 4.10: Return None for missing dates (no fallback)
    logger.debug("date_not_found")
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
