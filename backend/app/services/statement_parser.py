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
    """Parse amount string to Decimal, handling commas, Cr/Dr, and currency symbols."""
    if not val or not isinstance(val, str):
        return None
    s = val.strip().replace(",", "").replace(" ", "").upper()
    # Remove Cr/Dr suffix (indicates credit/debit in some statements)
    s = re.sub(r"\s*(CR|DR)\s*$", "", s, flags=re.I)
    # Remove currency symbols and common prefixes
    s = re.sub(r"^[₹$€£INR\.\s]+", "", s)
    s = re.sub(r"[₹$\s]", "", s)
    if not s or s in ("-", ".", "--"):
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(val: str) -> Optional[datetime]:
    """Parse date from various Indian bank formats."""
    if not val or not isinstance(val, str):
        return None
    s = val.strip()
    # Try longer formats first (for "15 Jan 2024" style)
    formats = [
        "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d/%b/%Y",  # 15 Jan 2024
        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y",
        "%d.%m.%Y", "%d %m %Y", "%Y/%m/%d",
        "%b %d, %Y", "%B %d, %Y",  # Jan 15, 2024
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s[:20].strip(), fmt)
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
    cols = _find_column_indices(headers)
    date_idx = cols["date"]
    debit_idx = cols["debit"]
    credit_idx = cols["credit"]
    amt_idx = cols["amount"] if (debit_idx is None or credit_idx is None) else None
    if amt_idx is None and (debit_idx is None or credit_idx is None):
        amt_idx = 1
    desc_idx = cols["desc"]

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


# Table extraction strategies for different PDF layouts (some have lines, some don't)
_TABLE_STRATEGIES = [
    None,  # Default: auto-detect (pass None to use extract_tables() default)
    {"vertical_strategy": "text", "horizontal_strategy": "text"},  # No lines, text-aligned
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},  # Explicit lines only
]

# Column name variants across Indian banks (HDFC, ICICI, SBI, Axis, Kotak, etc.)
_DATE_HEADERS = ["date", "transaction date", "posting date", "value date", "txn date", "trans date", "billing date", "post date"]
_AMOUNT_HEADERS = ["amount", "transaction amount", "txn amount", "balance"]
_DEBIT_HEADERS = ["debit", "withdrawal", "withdraw", "dr", "paid", "purchase", "charges"]
_CREDIT_HEADERS = ["credit", "deposit", "dep", "cr", "received", "refund", "payment"]
_DESC_HEADERS = ["description", "particulars", "narration", "remarks", "details", "transaction details", "transaction description", "ref", "particular", "narrative", "merchant", "payee"]


def _find_column_indices(headers: List[str]) -> dict:
    """Map column types to indices for varied bank formats."""
    h_lower = [str(h).strip().lower() if h else "" for h in headers]
    result = {"date": 0, "debit": None, "credit": None, "amount": None, "desc": len(h_lower) - 1}
    for i, h in enumerate(h_lower):
        if not h:
            continue
        if any(d in h for d in _DATE_HEADERS) or "date" in h:
            result["date"] = i
        elif any(x in h for x in _DEBIT_HEADERS):
            result["debit"] = i
        elif any(x in h for x in _CREDIT_HEADERS):
            result["credit"] = i
        elif any(a in h for a in _AMOUNT_HEADERS) or "amount" in h:
            result["amount"] = i
        elif any(d in h for d in _DESC_HEADERS) or "desc" in h or "particular" in h or "narration" in h:
            result["desc"] = i
    return result


def _row_to_transaction(
    row: List,
    cols: dict,
    seen: set,
) -> Optional[ParsedTransaction]:
    """Convert a table row to ParsedTransaction if valid."""
    date_str = str(row[cols["date"]]) if cols["date"] < len(row) else ""
    desc = ""
    for idx in [cols["desc"], len(row) - 1]:
        if idx is not None and idx < len(row) and row[idx]:
            desc = str(row[idx]).strip()
            break
    desc_lower = desc.lower()

    # Skip header/summary rows
    if not date_str or date_str.lower() in ("date", "transaction date", "posting date"):
        return None
    if any(x in desc_lower for x in ["opening balance", "closing balance", "total", "statement"]):
        return None

    tx_date = _parse_date(date_str)
    if not tx_date:
        return None

    amount = None
    tx_type = TransactionType.DEBIT
    if cols["debit"] is not None and cols["credit"] is not None:
        debit_val = _normalize_amount(str(row[cols["debit"]]) if cols["debit"] < len(row) else "") if cols["debit"] is not None else None
        credit_val = _normalize_amount(str(row[cols["credit"]]) if cols["credit"] < len(row) else "") if cols["credit"] is not None else None
        if debit_val and debit_val > 0:
            amount, tx_type = debit_val, TransactionType.DEBIT
        elif credit_val and credit_val > 0:
            amount, tx_type = credit_val, TransactionType.CREDIT
    elif cols["debit"] is not None:
        raw = str(row[cols["debit"]]) if cols["debit"] < len(row) else ""
        amount = _normalize_amount(raw)
        if amount and amount > 0:
            tx_type = TransactionType.DEBIT
    elif cols["credit"] is not None:
        raw = str(row[cols["credit"]]) if cols["credit"] < len(row) else ""
        amount = _normalize_amount(raw)
        if amount and amount > 0:
            tx_type = TransactionType.CREDIT
    elif cols["amount"] is not None:
        raw = str(row[cols["amount"]]) if cols["amount"] < len(row) else ""
        amount = _normalize_amount(raw)
        if amount and amount != 0:
            amount = abs(amount)
            tx_type = _infer_type(amount, desc_lower, [str(x) for x in row])

    if not amount or amount <= 0:
        return None

    key = (tx_date.date().isoformat(), str(amount), (desc or "")[:50])
    if key in seen:
        return None
    seen.add(key)
    return ParsedTransaction(
        amount=amount,
        currency="INR",
        transaction_type=tx_type,
        merchant=desc[:255] if desc else None,
        transaction_date=tx_date,
        bank_name=None,
        payment_method="Statement",
        raw_snippet=desc[:500] if desc else None,
    )


def _extract_from_text(text: str, seen: set) -> List[ParsedTransaction]:
    """Extract transactions from raw text when table extraction fails."""
    results = []
    # Multiple patterns for different bank formats
    patterns = [
        # DD-MM-YYYY or DD/MM/YYYY ... amount (with optional Cr/Dr)
        r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\s+.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:Cr|Dr)?",
        # DD Mon YYYY
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\s+.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:Cr|Dr)?",
        # Rs. 1,234.56 or ₹1234.56
        r"(?:Rs\.?|₹|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+.*?(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        # Amount at end: ... 1,234.56
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
            try:
                if len(m.groups()) == 2:
                    g1, g2 = m.group(1), m.group(2)
                    # First group is date if it starts with DD-MM or DD Mon
                    if re.match(r"\d{1,2}[-/\.]\d", g1) or re.match(r"\d{1,2}\s+[A-Za-z]{3}", g1):
                        date_str, amt_str = g1, g2
                        desc = None
                    else:
                        date_str, amt_str = g2, g1
                        desc = g1[:100] if re.match(r"\d", g1) is None else None
                else:
                    date_str, desc, amt_str = m.group(1), m.group(2), m.group(3)
                tx_date = _parse_date(date_str)
                amount = _normalize_amount(amt_str)
                if tx_date and amount and amount > 0:
                    key = (tx_date.date().isoformat(), str(amount))
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            ParsedTransaction(
                                amount=amount,
                                currency="INR",
                                transaction_type=TransactionType.DEBIT,
                                merchant=desc[:255] if desc else None,
                                transaction_date=tx_date,
                                bank_name=None,
                                payment_method="Statement",
                                raw_snippet=m.group(0)[:300],
                            )
                        )
            except (IndexError, AttributeError):
                continue
    return results


def parse_pdf_statement(
    content: bytes,
    filename: str = "",
    password: Optional[str] = None,
) -> List[ParsedTransaction]:
    """
    Parse bank/credit card statement PDF.
    Uses multiple extraction strategies to handle HDFC, ICICI, SBI, Axis, Kotak, etc.
    Supports password-protected PDFs via the password parameter.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber_not_installed")
        return []

    transactions: List[ParsedTransaction] = []
    seen: set = set()

    try:
        with pdfplumber.open(io.BytesIO(content), password=password or None) as pdf:
            for page in pdf.pages:
                page_transactions = []

                # Strategy 1: Try extract_tables with different settings
                for table_settings in _TABLE_STRATEGIES:
                    try:
                        tables = page.extract_tables(table_settings=table_settings) if table_settings is not None else page.extract_tables()
                    except Exception:
                        tables = page.extract_tables()
                    for table in tables or []:
                        if not table or len(table) < 2:
                            continue
                        headers = table[0]
                        cols = _find_column_indices(headers)
                        for row in table[1:]:
                            if not row:
                                continue
                            txn = _row_to_transaction(row, cols, seen)
                            if txn:
                                page_transactions.append(txn)
                        if page_transactions:
                            break
                    if page_transactions:
                        break

                # Strategy 2: Try find_tables (better for tables without clear lines)
                if not page_transactions:
                    try:
                        found = page.find_tables()
                        for tbl in found or []:
                            t = tbl.extract()
                            if t and len(t) >= 2:
                                headers = t[0]
                                cols = _find_column_indices(headers)
                                for row in t[1:]:
                                    if row:
                                        txn = _row_to_transaction(row, cols, seen)
                                        if txn:
                                            page_transactions.append(txn)
                                if page_transactions:
                                    break
                    except Exception:
                        pass

                # Strategy 3: Text-based fallback for non-tabular layouts
                if not page_transactions:
                    text = page.extract_text()
                    if text:
                        page_transactions = _extract_from_text(text, seen)

                transactions.extend(page_transactions)
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
