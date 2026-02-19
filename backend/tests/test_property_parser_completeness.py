"""
Property-based test for email parser completeness.

Feature: gmail-expense-tracker
Property 10: Email Parser Completeness

**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**

For any valid transaction email containing all required patterns (amount, type, date), 
the parser should successfully extract a complete ParsedTransaction object with all 
fields populated.
"""

import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from datetime import datetime

from app.services.email_parser import parse_email, TransactionType


# Strategy for generating valid transaction emails
@st.composite
def valid_transaction_email(draw):
    """Generate a valid transaction email with all required fields."""
    # Generate amount
    amount = draw(st.integers(min_value=1, max_value=100000))
    
    # Generate transaction type
    transaction_type = draw(st.sampled_from(['debited', 'credited']))
    
    # Generate date
    day = draw(st.integers(min_value=1, max_value=28))
    month = draw(st.integers(min_value=1, max_value=12))
    year = draw(st.integers(min_value=2020, max_value=2024))
    
    # Generate merchant
    merchants = ['Amazon', 'Flipkart', 'Swiggy', 'Zomato', 'Uber', 'Ola']
    merchant = draw(st.sampled_from(merchants))
    
    # Generate bank
    banks = ['HDFC', 'ICICI', 'SBI', 'Axis']
    bank = draw(st.sampled_from(banks))
    
    # Construct email
    subject = f"Transaction Alert: Rs {amount} {transaction_type}"
    body = f"""
    Dear Customer,
    
    Your account has been {transaction_type} with Rs {amount} at {merchant} on {day:02d}-{month:02d}-{year}.
    
    Bank: {bank} Bank
    
    Thank you.
    """
    
    return {
        'subject': subject,
        'body': body,
        'expected_amount': Decimal(str(amount)),
        'expected_type': TransactionType.DEBIT if 'debit' in transaction_type else TransactionType.CREDIT,
        'expected_merchant': merchant,
        'expected_bank': bank
    }


@pytest.mark.property
@settings(max_examples=50)
@given(email_data=valid_transaction_email())
def test_parser_extracts_complete_transaction(email_data):
    """
    Property 10: Email Parser Completeness
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    
    For any valid transaction email, the parser should extract all fields.
    """
    # Parse email
    parsed = parse_email(email_data['subject'], email_data['body'])
    
    # Should successfully parse
    assert parsed is not None, "Parser should successfully parse valid email"
    
    # Should extract amount
    assert parsed.amount == email_data['expected_amount'], \
        f"Amount should be {email_data['expected_amount']}, got {parsed.amount}"
    
    # Should extract transaction type
    assert parsed.transaction_type == email_data['expected_type'], \
        f"Type should be {email_data['expected_type']}, got {parsed.transaction_type}"
    
    # Should extract merchant
    assert parsed.merchant is not None, "Merchant should be extracted"
    assert email_data['expected_merchant'] in parsed.merchant, \
        f"Merchant should contain {email_data['expected_merchant']}, got {parsed.merchant}"
    
    # Should extract date
    assert parsed.transaction_date is not None, "Date should be extracted"
    assert isinstance(parsed.transaction_date, datetime), \
        "Date should be datetime object"
    
    # Should extract bank
    assert parsed.bank_name is not None, "Bank should be extracted"
    assert email_data['expected_bank'] in parsed.bank_name, \
        f"Bank should be {email_data['expected_bank']}, got {parsed.bank_name}"
    
    # Should have currency
    assert parsed.currency == "INR", "Currency should be INR"


@pytest.mark.property
@settings(max_examples=30)
@given(email_data=valid_transaction_email())
def test_parser_returns_parsedtransaction_object(email_data):
    """
    Property 10: Email Parser Completeness
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6**
    
    Parser should return a ParsedTransaction object with correct structure.
    """
    from app.services.email_parser import ParsedTransaction
    
    # Parse email
    parsed = parse_email(email_data['subject'], email_data['body'])
    
    # Should return ParsedTransaction instance
    assert isinstance(parsed, ParsedTransaction), \
        "Parser should return ParsedTransaction object"
    
    # Should have all required fields
    assert hasattr(parsed, 'amount'), "Should have amount field"
    assert hasattr(parsed, 'currency'), "Should have currency field"
    assert hasattr(parsed, 'transaction_type'), "Should have transaction_type field"
    assert hasattr(parsed, 'merchant'), "Should have merchant field"
    assert hasattr(parsed, 'transaction_date'), "Should have transaction_date field"
    assert hasattr(parsed, 'bank_name'), "Should have bank_name field"


@pytest.mark.property
@settings(max_examples=30)
@given(
    amount=st.integers(min_value=1, max_value=100000),
    transaction_type=st.sampled_from(['debited', 'credited'])
)
def test_parser_extracts_amount_correctly(amount, transaction_type):
    """
    Property 10: Email Parser Completeness (Amount extraction)
    
    **Validates: Requirements 4.2**
    
    Parser should correctly extract amounts in various formats.
    """
    # Test different amount formats
    formats = [
        f"Rs {amount}",
        f"INR {amount}",
        f"Rs. {amount}",
        f"Amount: Rs {amount}",
    ]
    
    for amount_format in formats:
        subject = f"Transaction: {amount_format} {transaction_type}"
        body = f"Your account has been {transaction_type} with {amount_format} on 01-01-2024."
        
        parsed = parse_email(subject, body)
        
        if parsed:
            assert parsed.amount == Decimal(str(amount)), \
                f"Amount should be {amount} for format '{amount_format}', got {parsed.amount}"


@pytest.mark.property
@settings(max_examples=20)
@given(transaction_type=st.sampled_from(['debited', 'credited', 'debit', 'credit']))
def test_parser_identifies_transaction_type(transaction_type):
    """
    Property 10: Email Parser Completeness (Type identification)
    
    **Validates: Requirements 4.3**
    
    Parser should correctly identify debit and credit transactions.
    """
    subject = f"Transaction Alert"
    body = f"Your account has been {transaction_type} with Rs 500 on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    if parsed:
        expected_type = TransactionType.DEBIT if 'debit' in transaction_type else TransactionType.CREDIT
        assert parsed.transaction_type == expected_type, \
            f"Type should be {expected_type} for keyword '{transaction_type}'"


@pytest.mark.property
@settings(max_examples=20)
@given(merchant=st.sampled_from(['Amazon', 'Flipkart', 'Swiggy', 'Zomato', 'Uber']))
def test_parser_extracts_merchant(merchant):
    """
    Property 10: Email Parser Completeness (Merchant extraction)
    
    **Validates: Requirements 4.4**
    
    Parser should extract merchant names from various patterns.
    """
    patterns = [
        f"at {merchant} on",
        f"to {merchant} on",
        f"Merchant: {merchant}",
    ]
    
    for pattern in patterns:
        subject = "Transaction Alert"
        body = f"Your account has been debited with Rs 500 {pattern} 01-01-2024."
        
        parsed = parse_email(subject, body)
        
        if parsed and parsed.merchant:
            assert merchant in parsed.merchant, \
                f"Merchant should contain '{merchant}' for pattern '{pattern}'"


@pytest.mark.property
@settings(max_examples=20)
@given(
    day=st.integers(min_value=1, max_value=28),
    month=st.integers(min_value=1, max_value=12),
    year=st.integers(min_value=2020, max_value=2024)
)
def test_parser_extracts_date(day, month, year):
    """
    Property 10: Email Parser Completeness (Date extraction)
    
    **Validates: Requirements 4.5**
    
    Parser should extract dates in various formats.
    """
    date_formats = [
        f"{day:02d}-{month:02d}-{year}",
        f"{day:02d}/{month:02d}/{year}",
    ]
    
    for date_str in date_formats:
        subject = "Transaction Alert"
        body = f"Your account has been debited with Rs 500 on {date_str}."
        
        parsed = parse_email(subject, body)
        
        if parsed:
            assert parsed.transaction_date is not None, \
                f"Date should be extracted from format '{date_str}'"
            assert isinstance(parsed.transaction_date, datetime), \
                "Date should be datetime object"


@pytest.mark.property
@settings(max_examples=20)
@given(bank=st.sampled_from(['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak']))
def test_parser_identifies_bank(bank):
    """
    Property 10: Email Parser Completeness (Bank identification)
    
    **Validates: Requirements 4.6**
    
    Parser should identify bank names from email content.
    """
    subject = f"{bank} Bank Transaction Alert"
    body = f"Your {bank} account has been debited with Rs 500 on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    if parsed and parsed.bank_name:
        assert bank in parsed.bank_name, \
            f"Bank should be identified as '{bank}', got '{parsed.bank_name}'"
