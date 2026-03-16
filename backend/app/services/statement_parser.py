"""
Bank and credit card statement parser for PDF and CSV files.

Supports common Indian bank formats (HDFC, ICICI, SBI, Axis, etc.)
and generic CSV layouts with date, amount, description columns.
"""

import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Optional
import structlog

from app.services.email_parser import ParsedTransaction, TransactionType

logger = structlog.get_logger()

# Max file sizes (bytes)
MAX_CSV_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB

# Allowed extensions
ALLOWED_EXTENSIONS = {".csv", ".pdf"}
ALLOWED_MIME = {"text/csv", "application/csv", "application/pdf"}


def _normalize_amount(val: str) -> Optional[Decimal]:
    """Parse amount string to Decimal, handling commas and signs."""
    if not val or not isinstance(val, str):
        return None
    s = val.strip().replace(",", "").replace(" ", "")
    # Remove currency symbols
    s = re.sub(r"[₹$\s]", "", s)
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(val: str) -> Optional[datetime]:
    """Parse date from various formats."""
    if not val or not isinstance(val, str):
        return None
    s = val.strip()
    formats = [
        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y",
        "%d-%b-%Y", "%d/%b/%Y", "%m/%d/%Y", "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s[:10], fmt)
            return dt.replace(hour=12, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _infer_type(amount: Decimal, desc_lower: str, col_names: List[str]) -> TransactionType:
    """Infer debit vs credit from context."""
    if amount < 0:
        return TransactionType.CREDIT
    if amount > 0:
        return TransactionType.DEBIT
    # Check column names / description
    debit_hints = ["debit", "withdraw", "payment", "purchase", "dr", "paid", "spent"]
    credit_hints = ["credit", "deposit", "received", "refund", "cr"]
    d = desc_lower
    for h in debit_hints:
        if h in d:
            return TransactionType.DEBIT
    for h in credit_hints:
        if h in d:
            return TransactionType.CREDIT
    return TransactionType.DEBIT  # default


def parse_csv_statement(
    content: bytes,
    filename: str = "",
) -> List[ParsedTransaction]:
    """
    Parse bank/credit card statement CSV.
    Tries common column layouts: Date, Amount, Description, etc.
    """
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("statement_csv_decode_failed", error=str(e))
        return []

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if len(rows) < 2:
        return []

    headers = [h.strip().lower() for h in rows[0]]
    # Map common column names to indices
    date_cols = ["date", "transaction date", "posting date", "value date", "txn date"]
    amt_cols = ["amount", "debit", "credit", "balance", "withdrawal", "deposit"]
    desc_cols = ["description", "particulars", "narration", "remarks", "details", "transaction details"]

    date_idx = next((i for i, h in enumerate(headers) if h in date_cols or "date" in h), None)
    amt_idx = next((i for i, h in enumerate(headers) if h in amt_cols or "amount" in h or "debit" in h or "credit" in h), None)
    desc_idx = next((i for i, h in enumerate(headers) if h in desc_cols or "desc" in h or "narration" in h), None)

    # Some banks have separate Debit/Credit columns
    debit_idx = next((i for i, h in enumerate(headers) if h == "debit"), None)
    credit_idx = next((i for i, h in enumerate(headers) if h == "credit"), None)
    if debit_idx is not None and credit_idx is not None:
        amt_idx = None  # Use debit/credit columns

    if date_idx is None:
        date_idx = 0
    if amt_idx is None and debit_idx is None:
        amt_idx = 1
    if desc_idx is None:
        desc_idx = max(0, len(headers) - 1)

    transactions: List[ParsedTransaction] = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= max(date_idx, amt_idx or 0, desc_idx):
            continue
        try:
            date_str = row[date_idx] if date_idx < len(row) else ""
            desc = row[desc_idx] if desc_idx < len(row) else ""
            desc_lower = desc.lower()

            # Skip header-like or summary rows
            if not date_str or date_str.lower() in ("date", "transaction date"):
                continue
            if "opening balance" in desc_lower or "closing balance" in desc_lower:
                continue

            tx_date = _parse_date(date_str)
            if not tx_date:
                continue

            amount = None
            tx_type = TransactionType.DEBIT
            if debit_idx is not None and credit_idx is not None:
                debit_val = _normalize_amount(row[debit_idx]) if debit_idx < len(row) else None
                credit_val = _normalize_amount(row[credit_idx]) if credit_idx < len(row) else None
                if debit_val and debit_val > 0:
                    amount = debit_val
                    tx_type = TransactionType.DEBIT
                elif credit_val and credit_val > 0:
                    amount = credit_val
                    tx_type = TransactionType.CREDIT
            elif amt_idx is not None:
                raw = row[amt_idx] if amt_idx < len(row) else ""
                amount = _normalize_amount(raw)
                if amount is not None and amount != 0:
                    amount = abs(amount)
                    tx_type = _infer_type(Decimal(str(amount)), desc_lower, headers)

            if amount is None or amount <= 0:
                continue

            transactions.append(
                ParsedTransaction(
                    amount=amount,
                    currency="INR",
                    transaction_type=tx_type,
                    merchant=desc[:255] if desc else None,
                    transaction_date=tx_date,
                    bank_name=None,
                    payment_method="Statement",
                    raw_snippet=desc[:500] if desc else None,
                )
            )
        except Exception as e:
            logger.debug("statement_row_skip", row_index=i, error=str(e))

    return transactions


def parse_pdf_statement(
    content: bytes,
    filename: str = "",
    password: Optional[str] = None,
) -> List[ParsedTransaction]:
    """
    Parse bank/credit card statement PDF.
    Extracts text and tables using pdfplumber.
    Supports password-protected PDFs via the password parameter.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber_not_installed")
        return []

    transactions: List[ParsedTransaction] = []
    seen: set = set()  # (date, amount, desc) for dedup

    try:
        with pdfplumber.open(io.BytesIO(content), password=password or None) as pdf:
            for page in pdf.pages:
                # Try tables first
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers = [str(h).strip().lower() if h else "" for h in table[0]]
                    date_idx = next((i for i, h in enumerate(headers) if "date" in h), 0)
                    amt_idx = next((i for i, h in enumerate(headers) if "amount" in h or "debit" in h or "credit" in h), 1)
                    desc_idx = next((i for i, h in enumerate(headers) if "desc" in h or "particular" in h or "narration" in h), len(headers) - 1)

                    for row in table[1:]:
                        if not row or len(row) <= max(date_idx, amt_idx, desc_idx):
                            continue
                        date_str = str(row[date_idx]) if date_idx < len(row) else ""
                        amt_str = str(row[amt_idx]) if amt_idx < len(row) else ""
                        desc = str(row[desc_idx]) if desc_idx < len(row) else ""
                        tx_date = _parse_date(date_str)
                        amount = _normalize_amount(amt_str)
                        if tx_date and amount and amount > 0:
                            key = (tx_date.date().isoformat(), str(amount), desc[:50])
                            if key not in seen:
                                seen.add(key)
                                transactions.append(
                                    ParsedTransaction(
                                        amount=amount,
                                        currency="INR",
                                        transaction_type=TransactionType.DEBIT,
                                        merchant=desc[:255] if desc else None,
                                        transaction_date=tx_date,
                                        bank_name=None,
                                        payment_method="Statement",
                                        raw_snippet=desc[:500] if desc else None,
                                    )
                                )

                # Fallback: extract text and look for amount patterns
                text = page.extract_text()
                if not text:
                    continue
                # Pattern: DD-MM-YYYY or DD/MM/YYYY ... amount
                pattern = r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
                for m in re.finditer(pattern, text):
                    date_str, amt_str = m.group(1), m.group(2)
                    tx_date = _parse_date(date_str)
                    amount = _normalize_amount(amt_str)
                    if tx_date and amount and amount > 0:
                        key = (tx_date.date().isoformat(), str(amount))
                        if key not in seen:
                            seen.add(key)
                            transactions.append(
                                ParsedTransaction(
                                    amount=amount,
                                    currency="INR",
                                    transaction_type=TransactionType.DEBIT,
                                    merchant=None,
                                    transaction_date=tx_date,
                                    bank_name=None,
                                    payment_method="Statement",
                                    raw_snippet=m.group(0)[:200],
                                )
                            )
    except ValueError:
        raise
    except Exception as e:
        err_msg = str(e).lower()
        if "password" in err_msg or "encrypted" in err_msg or "decrypt" in err_msg or "wrong password" in err_msg:
            raise ValueError(
                "This PDF is password-protected. Please provide the correct password to unlock it."
            ) from e
        logger.error("statement_pdf_parse_failed", error=str(e), exc_info=True)

    return transactions
