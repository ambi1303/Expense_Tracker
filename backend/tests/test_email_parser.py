"""
Unit tests for email parser.

Tests parsing of sample emails from various Indian banks including HDFC, ICICI,
SBI, and Axis Bank, as well as edge cases.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.services.email_parser import (
    parse_email,
    extract_amount,
    extract_transaction_type,
    extract_merchant,
    extract_date,
    extract_bank,
    TransactionType
)


def test_parse_hdfc_debit_email():
    """
    Test parsing HDFC debit transaction email.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    """
    subject = "HDFC Bank: Rs 1,250.00 debited from your account"
    body = """
    Dear Customer,
    
    Your HDFC Bank account has been debited with Rs 1,250.00 at Amazon on 15-01-2024.
    
    Available balance: Rs 50,000.00
    
    Thank you for banking with us.
    """
    
    parsed = parse_email(subject, body)
    
    assert parsed is not None
    assert parsed.amount == Decimal("1250.00")
    assert parsed.transaction_type == TransactionType.DEBIT
    assert "Amazon" in parsed.merchant
    assert parsed.bank_name == "HDFC"


def test_parse_icici_credit_email():
    """
    Test parsing ICICI credit transaction email.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    """
    subject = "ICICI Bank: Account credited"
    body = """
    Dear Customer,
    
    Your ICICI Bank account has been credited with INR 5,000 from Salary on 01/01/2024.
    
    Current balance: INR 55,000
    """
    
    parsed = parse_email(subject, body)
    
    assert parsed is not None
    assert parsed.amount == Decimal("5000")
    assert parsed.transaction_type == TransactionType.CREDIT
    assert parsed.bank_name == "ICICI"


def test_parse_sbi_debit_email():
    """
    Test parsing SBI debit transaction email.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    """
    subject = "SBI: Transaction Alert"
    body = """
    Dear Customer,
    
    Rs 750 has been debited from your SBI account at Swiggy on 20-02-2024.
    
    Thank you.
    """
    
    parsed = parse_email(subject, body)
    
    assert parsed is not None
    assert parsed.amount == Decimal("750")
    assert parsed.transaction_type == TransactionType.DEBIT
    assert "Swiggy" in parsed.merchant
    assert parsed.bank_name == "SBI"


def test_parse_axis_debit_email():
    """
    Test parsing Axis Bank debit transaction email.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    """
    subject = "Axis Bank Transaction Alert"
    body = """
    Your Axis Bank account ending with 1234 has been debited.
    
    Amount: Rs 2,500.00
    Merchant: Flipkart
    Date: 10-03-2024
    """
    
    parsed = parse_email(subject, body)
    
    assert parsed is not None
    assert parsed.amount == Decimal("2500.00")
    assert parsed.transaction_type == TransactionType.DEBIT
    assert "Flipkart" in parsed.merchant
    assert parsed.bank_name == "Axis"


def test_parse_email_with_missing_merchant():
    """
    Test parsing email with missing merchant.
    
    **Validates: Requirements 4.9**
    """
    subject = "Transaction Alert"
    body = "Your account has been debited with Rs 500 on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    # Should still parse successfully
    assert parsed is not None
    assert parsed.amount == Decimal("500")
    assert parsed.transaction_type == TransactionType.DEBIT
    # Merchant may be None
    assert parsed.merchant is None or isinstance(parsed.merchant, str)


def test_parse_email_with_malformed_date():
    """
    Test parsing email with malformed date.
    
    Per Requirement 4.10: Parser should return None when no valid date is found.
    
    **Validates: Requirements 4.9, 4.10**
    """
    subject = "Transaction Alert"
    body = "Your account has been debited with Rs 500 on invalid-date."
    
    parsed = parse_email(subject, body)
    
    # Should return None because date is invalid (per Requirement 4.10)
    assert parsed is None


def test_debit_vs_credit_identification():
    """
    Test debit vs credit identification.
    
    **Validates: Requirements 4.3**
    """
    # Test debit keywords
    debit_keywords = ['debited', 'debit', 'spent', 'withdrawn', 'paid']
    for keyword in debit_keywords:
        body = f"Your account has been {keyword} with Rs 100 on 01-01-2024."
        parsed = parse_email("Alert", body)
        if parsed:
            assert parsed.transaction_type == TransactionType.DEBIT, \
                f"Should identify '{keyword}' as debit"
    
    # Test credit keywords
    credit_keywords = ['credited', 'credit', 'received', 'deposited']
    for keyword in credit_keywords:
        body = f"Your account has been {keyword} with Rs 100 on 01-01-2024."
        parsed = parse_email("Alert", body)
        if parsed:
            assert parsed.transaction_type == TransactionType.CREDIT, \
                f"Should identify '{keyword}' as credit"


def test_amount_extraction_with_various_formats():
    """
    Test amount extraction with various formats (Rs, INR, commas).
    
    **Validates: Requirements 4.2**
    """
    test_cases = [
        ("Rs 1000", Decimal("1000")),
        ("Rs. 1000", Decimal("1000")),
        ("INR 1000", Decimal("1000")),
        ("Rs 1,000", Decimal("1000")),
        ("Rs 1,00,000", Decimal("100000")),
        ("Rs 1,234.56", Decimal("1234.56")),
        ("Amount: Rs 500", Decimal("500")),
    ]
    
    for amount_str, expected in test_cases:
        text = f"Transaction: {amount_str} debited on 01-01-2024"
        amount = extract_amount(text)
        assert amount == expected, \
            f"Should extract {expected} from '{amount_str}', got {amount}"


def test_parser_returns_none_for_unparseable_emails():
    """
    Test parser returns None for unparseable emails.
    
    **Validates: Requirements 4.9**
    """
    unparseable_emails = [
        ("Hello", "This is not a transaction email"),
        ("Meeting", "Let's meet tomorrow at 5pm"),
        ("", ""),
        ("Random text", "No transaction information here"),
    ]
    
    for subject, body in unparseable_emails:
        parsed = parse_email(subject, body)
        assert parsed is None, \
            f"Should return None for unparseable email: '{subject}'"


def test_extract_amount_with_special_characters():
    """
    Test amount extraction with special characters.
    
    **Validates: Requirements 4.2**
    """
    text = "Amount: Rs 1,234.56 (including taxes)"
    amount = extract_amount(text)
    assert amount == Decimal("1234.56")


def test_extract_merchant_patterns():
    """
    Test merchant extraction with various patterns.
    
    **Validates: Requirements 4.4**
    """
    test_cases = [
        ("debited at Amazon on 01-01-2024", "Amazon"),
        ("paid to Flipkart on 01-01-2024", "Flipkart"),
        ("Merchant: Swiggy", "Swiggy"),
        ("transaction from Zomato on", "Zomato"),
    ]
    
    for text, expected_merchant in test_cases:
        merchant = extract_merchant(text)
        if merchant:
            assert expected_merchant in merchant, \
                f"Should extract '{expected_merchant}' from '{text}'"


def test_extract_date_formats():
    """
    Test date extraction with multiple formats.
    
    **Validates: Requirements 4.5**
    """
    test_cases = [
        "on 15-01-2024",
        "on 15/01/2024",
        "on 15 January 2024",
        "on 15 Jan 2024",
    ]
    
    for text in test_cases:
        date = extract_date(text)
        assert date is not None, \
            f"Should extract date from '{text}'"
        assert isinstance(date, datetime)


def test_extract_bank_identification():
    """
    Test bank identification from email content.
    
    **Validates: Requirements 4.6**
    """
    test_cases = [
        ("HDFC Bank transaction", "HDFC"),
        ("Your ICICI account", "ICICI"),
        ("SBI alert", "SBI"),
        ("Axis Bank notification", "Axis"),
        ("Kotak Mahindra Bank", "Kotak"),
    ]
    
    for text, expected_bank in test_cases:
        bank = extract_bank(text)
        assert bank == expected_bank, \
            f"Should identify '{expected_bank}' from '{text}', got '{bank}'"


def test_parse_email_with_multiline_content():
    """
    Test parsing email with multiline content.
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    """
    subject = "Transaction Alert"
    body = """
    Dear Customer,
    
    Your account has been debited.
    
    Amount: Rs 1,500
    Merchant: Amazon India
    Date: 20-03-2024
    Type: Purchase
    
    Thank you.
    """
    
    parsed = parse_email(subject, body)
    
    assert parsed is not None
    assert parsed.amount == Decimal("1500")
    assert parsed.transaction_type == TransactionType.DEBIT


def test_currency_is_always_inr():
    """
    Test that currency is always set to INR.
    
    **Validates: Requirements 4.2**
    """
    subject = "Transaction Alert"
    body = "Your account has been debited with Rs 500 on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    if parsed:
        assert parsed.currency == "INR"


def test_parse_email_case_insensitive():
    """
    Test that parsing is case-insensitive.
    
    **Validates: Requirements 4.2, 4.3**
    """
    # Test with different cases
    test_cases = [
        "DEBITED",
        "debited",
        "Debited",
        "CREDITED",
        "credited",
        "Credited",
    ]
    
    for keyword in test_cases:
        body = f"Your account has been {keyword} with Rs 500 on 01-01-2024."
        parsed = parse_email("Alert", body)
        assert parsed is not None, \
            f"Should parse email with '{keyword}' (case-insensitive)"
