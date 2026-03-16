"""
Email parser for extracting transaction details from bank emails.

This module provides functions to parse transaction emails from Indian banks
and extract structured transaction data including amount, type, merchant, date, and bank.
"""

import re
from typing import Optional, List
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
    """Structured transaction data extracted from email or statement."""
    amount: Decimal
    currency: str = "INR"
    transaction_type: TransactionType
    merchant: Optional[str] = None
    transaction_date: datetime
    bank_name: Optional[str] = None
    account_label: Optional[str] = None  # e.g. "HDFC Credit Card", "ICICI Savings"
    category: Optional[str] = None
    payment_method: Optional[str] = None
    upi_reference: Optional[str] = None
    raw_snippet: Optional[str] = None


# Regex patterns for extracting transaction details (INR and multi-currency)
CURRENCY_SYMBOLS = r'(?:INR|Rs\.?|₹|USD|\$|EUR|€|GBP|£)'
AMOUNT_PATTERNS = [
    rf'{CURRENCY_SYMBOLS}\s*(\d+(?:,\d+)*(?:\.\d{{2}})?)',
    r'(?:amount|Amount|AMOUNT):\s*(?:INR|Rs\.?|₹|USD|EUR|GBP)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    r'(?:debited|credited)\s+(?:with\s+)?(?:INR|Rs\.?|₹|USD|EUR|GBP)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
    rf'{CURRENCY_SYMBOLS}(\d+(?:,\d+)*(?:\.\d{{2}})?)',
]

DEBIT_KEYWORDS = ['debited', 'debit', 'spent', 'withdrawn', 'paid', 'purchase']
CREDIT_KEYWORDS = ['credited', 'credit', 'received', 'deposited', 'refund']

MERCHANT_PATTERNS = [
    r'(?:at|to|from)\s+([A-Za-z0-9][A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+dated|\s+for)',
    r'(?:merchant|Merchant|MERCHANT):\s*([A-Za-z0-9\s&\-\.]+)',
    r'(?:paid to|Paid to|PAID TO)\s+([A-Za-z0-9\s&\-\.]+)',
    r'UPI[/\s]+[a-zA-Z0-9\.\-]*[/\s]+([A-Za-z0-9][A-Za-z0-9\s&\-\.]{2,50})',  # UPI/xxx/Merchant
    r'(?:to|at)\s+([A-Za-z0-9][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:on|for|via|using))',
    r'(?:at\s+)?([A-Za-z]+\.(?:com|in|co\.in|net))\s+(?:on|for|dated)',  # domain as merchant
    r'(?:VPA|vpa)[\s:]+([a-zA-Z0-9\.\-]+@[a-zA-Z0-9\.\-]+)',  # UPI VPA
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


def extract_currency(text: str) -> str:
    """
    Detect currency from email text. Defaults to INR for Indian banks.
    """
    text_upper = text.upper()
    if 'USD' in text_upper or '$' in text or 'US$' in text_upper:
        return "USD"
    if 'EUR' in text_upper or '€' in text:
        return "EUR"
    if 'GBP' in text_upper or '£' in text:
        return "GBP"
    return "INR"


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


def _split_transaction_blocks(text: str) -> List[str]:
    """
    Split email text into blocks that may each contain a transaction.
    Splits on boundaries where a new transaction typically starts (amount + debited/credited).
    """
    blocks = []
    # Split on newline sequences (paragraph breaks) - each para may be a transaction
    raw_blocks = re.split(r'\n\s*\n', text)
    for block in raw_blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue
        # Block must have currency and transaction keyword
        if re.search(r'(?:INR|Rs\.?|₹|USD|\$|EUR|€|GBP|£)', block, re.I) and \
           re.search(r'\b(?:debit|credit)(?:ed)?\b', block, re.I):
            blocks.append(block)
    
    # If no blocks found, treat whole text as one block
    if not blocks and text.strip():
        blocks = [text]
    return blocks


def parse_emails(subject: str, body: str) -> List[ParsedTransaction]:
    """
    Parse email content to extract possibly multiple transactions.
    
    Returns a list of ParsedTransaction objects. Many emails have one transaction;
    some (e.g. summaries) may have multiple.
    """
    logger.info("parse_emails_started")
    
    subject = _strip_html(subject)
    body = _strip_html(body)
    text = f"{subject}\n{body}"
    
    if _is_non_transaction_email(text):
        logger.info("parse_emails_rejected_non_transaction")
        return []
    
    if not re.search(r'\b(?:INR|Rs\.?|₹|USD|\$|EUR|€|GBP|£)\b', text, re.IGNORECASE):
        return []
    
    if not re.search(r'\b(?:debit|credit)(?:ed)?\b', text, re.IGNORECASE):
        return []
    
    primary_date = extract_date(text)
    primary_bank = extract_bank(text)
    primary_currency = extract_currency(text)
    seen = set()  # (amount, type, date) to avoid duplicates
    
    results = []
    blocks = _split_transaction_blocks(text)
    
    for block in blocks:
        tx_type = extract_transaction_type(block)
        amount = extract_amount(block, tx_type)
        tx_date = extract_date(block) or primary_date
        
        if not amount or not tx_type or not tx_date:
            continue
        
        key = (str(amount), tx_type.value, tx_date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        
        merchant = extract_merchant(block)
        bank = extract_bank(block) or primary_bank
        account_label = extract_account_label(block, bank)
        upi_ref = extract_upi_reference(block)
        payment_method = extract_payment_method(block)
        category = auto_categorize(merchant, block)
        raw_snippet = block[:500] if len(block) > 500 else block

        results.append(ParsedTransaction(
            amount=amount,
            currency=extract_currency(block) or primary_currency,
            transaction_type=tx_type,
            merchant=merchant,
            transaction_date=tx_date,
            bank_name=bank,
            account_label=account_label,
            category=category,
            payment_method=payment_method,
            upi_reference=upi_ref,
            raw_snippet=raw_snippet
        ))
    
    if results:
        logger.info("parse_emails_success", count=len(results))
    return results


def parse_email(subject: str, body: str) -> Optional[ParsedTransaction]:
    """
    Parse email content to extract transaction details.
    Uses parse_emails and returns the first (primary) transaction if any.
    
    Args:
        subject: Email subject line.
        body: Email body content.
        
    Returns:
        ParsedTransaction object if parsing succeeds, None otherwise.
    """
    parsed_list = parse_emails(subject, body)
    return parsed_list[0] if parsed_list else None
    
    try:
        parsed_list = parse_emails(subject, body)
        return parsed_list[0] if parsed_list else None
    except (ValueError, TypeError) as e:
        logger.error("parse_email_failed", error=str(e), error_type=type(e).__name__)
        return None
    except Exception as e:
        logger.error("parse_email_unexpected_error", error=str(e), error_type=type(e).__name__)
        raise


def extract_amount(text: str, transaction_type: Optional[TransactionType] = None) -> Optional[Decimal]:
    """
    Extract transaction amount from text using regex patterns.
    
    When transaction_type is provided, prefers amounts that appear near the
    matching keyword (debited for debit, credited for credit) to fix
    amount+type coupling in emails with both debit and credit.
    
    Args:
        text: Text to extract amount from.
        transaction_type: Optional hint to prefer amounts near matching type keyword.
        
    Returns:
        Decimal amount if found, None otherwise.
    """
    amounts_with_context = []
    
    # Type-specific keywords (for amount+type coupling)
    debit_keywords = ['debited', 'debit', 'withdrawn', 'paid', 'purchase', 'charged']
    credit_keywords = ['credited', 'credit', 'received', 'deposited', 'refund']
    
    strong_transaction_keywords = debit_keywords + credit_keywords
    
    skip_keywords = [
        'available balance', 'current balance', 'balance:', 'balance is',
        'discount applied', 'discount:', 'discount ', 'discount of',
        'cashback', 'reward', 'points',
        'limit', 'minimum due', 'order total', 'order amount', 'order value',
        'order:', 'order '
    ]
    
    for pattern in AMOUNT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = Decimal(amount_str)
                if amount <= 0:
                    continue
                
                start_pos = max(0, match.start() - 80)
                end_pos = min(len(text), match.end() + 80)
                context = text[start_pos:end_pos].lower()
                
                has_strong_keyword = any(kw in context for kw in strong_transaction_keywords)
                has_skip_keyword = any(skip_kw in context for skip_kw in skip_keywords)
                
                if has_skip_keyword and not has_strong_keyword:
                    continue
                
                # Check if amount context matches the desired transaction type
                matches_type = False
                if transaction_type == TransactionType.DEBIT:
                    matches_type = any(kw in context for kw in debit_keywords)
                elif transaction_type == TransactionType.CREDIT:
                    matches_type = any(kw in context for kw in credit_keywords)
                
                amounts_with_context.append({
                    'amount': amount,
                    'position': match.start(),
                    'context': context,
                    'has_strong_keyword': has_strong_keyword,
                    'matches_type': matches_type
                })
            except (ValueError, TypeError, ArithmeticError):
                continue
    
    if not amounts_with_context:
        return None
    
    # Strategy 1: If type hint given, prefer amounts that match that type
    if transaction_type:
        type_matched = [a for a in amounts_with_context if a['matches_type']]
        if type_matched:
            smallest_matched = min(type_matched, key=lambda x: x['amount'])
            logger.debug("amount_selected_type_matched", amount=smallest_matched['amount'])
            return smallest_matched['amount']
    
    # Strategy 2: Prioritize amounts with strong transaction keywords
    strong_amounts = [a for a in amounts_with_context if a['has_strong_keyword']]
    if strong_amounts:
        smallest_strong = min(strong_amounts, key=lambda x: x['amount'])
        logger.debug("amount_selected_strong_keyword", amount=smallest_strong['amount'])
        return smallest_strong['amount']
    
    # Strategy 3: Fallback to smallest amount
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


def extract_account_label(text: str, bank_name: Optional[str] = None) -> Optional[str]:
    """
    Build account label from bank + card/product type (e.g. "HDFC Credit Card", "ICICI Savings").
    Helps distinguish multiple accounts and cards from the same bank.

    Args:
        text: Email or statement text.
        bank_name: Bank already identified by extract_bank.

    Returns:
        Account label string, e.g. "HDFC Credit Card", "SBI Debit", or "HDFC Bank".
    """
    text_lower = text.lower()
    bank = bank_name or extract_bank(text)
    if not bank:
        return None

    # Credit card indicators
    if any(kw in text_lower for kw in ['credit card', 'cred card', 'cc ', 'card ending', 'card no']):
        return f"{bank} Credit Card"
    # Debit card
    if any(kw in text_lower for kw in ['debit card', 'atm card', 'atm withdrawal']):
        return f"{bank} Debit"
    # Savings
    if any(kw in text_lower for kw in ['savings', 'sb account', 'current account']):
        return f"{bank} Savings"
    # UPI often from primary account
    if any(kw in text_lower for kw in ['upi', 'imps', 'neft', 'rtgs']):
        return f"{bank} (UPI/Transfer)"

    return f"{bank} Bank"
