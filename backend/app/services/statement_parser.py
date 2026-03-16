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
    """
    Infer debit vs credit from amount sign, description, or column names.
    Handles different bank terminologies: Withdrawal/Deposit, Dr/Cr, Debit/Credit, etc.
    """
    if amount < 0:
        return TransactionType.CREDIT
    if amount > 0:
        return TransactionType.DEBIT
    # Check description (narration often contains type keywords)
    d = desc_lower
    # Money out (debit)
    debit_hints = [
        "debit", "withdrawal", "withdrawn", "withdraw", "dr ", " dr", ".dr",
        "payment", "paid", "purchase", "purchases", "charges", "spent",
        "debited", "out", "transfer out", "neft outward", "imps paid",
    ]
    # Money in (credit)
    credit_hints = [
        "credit", "deposit", "deposited", "dep ", " cr", ".cr",
        "received", "refund", "credited", "interest", "in",
        "transfer in", "neft inward", "imps received", "upi received",
        "salary", "dividend",
    ]
    for h in debit_hints:
        if h in d:
            return TransactionType.DEBIT
    for h in credit_hints:
        if h in d:
            return TransactionType.CREDIT
    # Check column names for context
    cols_str = " ".join(str(c).lower() for c in col_names)
    if any(x in cols_str for x in ["withdrawal", "withdraw", "debit", "dr", "paid"]):
        return TransactionType.DEBIT
    if any(x in cols_str for x in ["deposit", "credit", "cr", "received", "refund"]):
        return TransactionType.CREDIT
    return TransactionType.DEBIT  # default for single amount column


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
    type_idx = cols.get("type")

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
                    # Use type column (Dr/Cr, Debit/Credit, Withdrawal/Deposit) if present
                    if type_idx is not None and type_idx < len(row):
                        type_val = str(row[type_idx]).strip() if row[type_idx] else ""
                        if _is_debit_type(type_val):
                            tx_type = TransactionType.DEBIT
                        elif _is_credit_type(type_val):
                            tx_type = TransactionType.CREDIT
                        else:
                            tx_type = _infer_type(Decimal(str(amount)), desc_lower, headers)
                    else:
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

# Column name variants across Indian banks (HDFC, ICICI, SBI, Axis, Kotak, Yes, IDFC, etc.)
# Banks use different terms: Debit/Credit, Withdrawal/Deposit, Dr/Cr, Out/In, Paid/Received
_DATE_HEADERS = ["date", "transaction date", "posting date", "value date", "txn date", "trans date", "billing date", "post date", "value date"]
_AMOUNT_HEADERS = ["amount", "transaction amount", "txn amount", "balance", "value"]
# Money OUT (expense): Debit, Withdrawal, Dr, Purchases, Charges, Paid, etc.
_DEBIT_HEADERS = [
    "debit", "debit amount", "withdrawal", "withdrawals", "withdraw", "withdrawn",
    "dr", "d.r.", "out", "outflow", "paid", "purchase", "purchases", "charges",
    "spent", "expenses", "expense", "withdrawal amount", "debits",
    "payment",  # Some banks: "Payment" = amount you paid (debit)
]
# Money IN (income): Credit, Deposit, Cr, Refund, Received, etc.
_CREDIT_HEADERS = [
    "credit", "credit amount", "deposit", "deposits", "dep.",
    "cr", "c.r.", "in", "inflow", "received", "refund", "refunds",
    "deposit amount", "credits", "interest", "interest credited",
    "payments",  # Credit card: "Payments" = payments you made to card (credit)
]
# Transaction type column: contains values like "DR"/"CR"/"Debit"/"Credit"/"Withdrawal"/"Deposit"
_TYPE_HEADERS = ["type", "transaction type", "txn type", "entry", "dr/cr", "d/c", "debit/credit"]
_DESC_HEADERS = ["description", "particulars", "narration", "remarks", "details", "transaction details", "transaction description", "ref", "particular", "narrative", "merchant", "payee"]


def _is_debit_type(val: str) -> bool:
    """Return True if cell value indicates debit (money out)."""
    v = (val or "").strip().upper()
    if not v:
        return False
    debits = ("D", "DR", "DEBIT", "DB", "DEB", "WITHDRAWAL", "WITHDRAW", "OUT", "PAID", "CHARGES", "PURCHASE", "PURCHASES")
    return v in debits or v.startswith("DR") or v.startswith("DEBIT")


def _is_credit_type(val: str) -> bool:
    """Return True if cell value indicates credit (money in)."""
    v = (val or "").strip().upper()
    if not v:
        return False
    credits = ("C", "CR", "CREDIT", "CRED", "DEPOSIT", "DEP", "IN", "RECEIVED", "REFUND", "CREDITED", "PAYMENT")
    return v in credits or v.startswith("CR") or v.startswith("CREDIT")


def _find_column_indices(headers: List[str]) -> dict:
    """Map column types to indices for varied bank formats."""
    h_lower = [str(h).strip().lower() if h else "" for h in headers]
    result = {"date": 0, "debit": None, "credit": None, "amount": None, "type": None, "desc": len(h_lower) - 1}
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
        elif any(t in h for t in _TYPE_HEADERS):
            result["type"] = i
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
            # Prefer type column (Dr/Cr, Debit/Credit, Withdrawal/Deposit) over inference
            if cols["type"] is not None and cols["type"] < len(row):
                type_val = str(row[cols["type"]]).strip() if row[cols["type"]] else ""
                if _is_debit_type(type_val):
                    tx_type = TransactionType.DEBIT
                elif _is_credit_type(type_val):
                    tx_type = TransactionType.CREDIT
                else:
                    tx_type = _infer_type(amount, desc_lower, [str(x) for x in row])
            else:
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
    # Multiple patterns for different bank formats (capture Cr/Dr for debit/credit)
    def _add_from_match(m, date_str: str, amt_str: str, desc: Optional[str], crdr: str):
        tx_date = _parse_date(date_str)
        amount = _normalize_amount(amt_str)
        if tx_date and amount and amount > 0:
            tx_type = TransactionType.CREDIT if (crdr or "").strip().upper() == "CR" else TransactionType.DEBIT
            key = (tx_date.date().isoformat(), str(amount))
            if key not in seen:
                seen.add(key)
                results.append(
                    ParsedTransaction(
                        amount=amount,
                        currency="INR",
                        transaction_type=tx_type,
                        merchant=desc[:255] if desc else None,
                        transaction_date=tx_date,
                        bank_name=None,
                        payment_method="Statement",
                        raw_snippet=m.group(0)[:300],
                    )
                )

    patterns = [
        # DD-MM-YYYY ... amount Cr/Dr
        r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\s+.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(Cr|Dr)?",
        # DD Mon YYYY ... amount Cr/Dr
        r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\s+.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(Cr|Dr)?",
        # Rs. amount ... date
        r"(?:Rs\.?|₹|INR)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+.*?(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        # date desc amount Cr/Dr
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(Cr|Dr)?\s*$",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
            try:
                g = m.groups()
                if len(g) == 2:
                    # Rs. amount date
                    amt_str, date_str = g[0], g[1]
                    _add_from_match(m, date_str, amt_str, None, "")
                elif len(g) == 3:
                    date_str, amt_str = g[0], g[1]
                    crdr = (g[2] or "").strip()
                    _add_from_match(m, date_str, amt_str, None, crdr)
                elif len(g) >= 4:
                    date_str, desc, amt_str = g[0], g[1], g[2]
                    crdr = (g[3] or "").strip()
                    _add_from_match(m, date_str, amt_str, desc, crdr)
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
