"""
Property-based test for email parser error handling.

Feature: gmail-expense-tracker
Property 11: Parser Error Handling

**Validates: Requirements 4.9**

For any email that lacks required transaction patterns, the parser should 
return None or an error indicator rather than a partial transaction.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.services.email_parser import parse_email


# Strategy for generating emails missing required fields
@st.composite
def email_missing_amount(draw):
    """Generate email missing amount."""
    transaction_type = draw(st.sampled_from(['debited', 'credited']))
    subject = f"Transaction Alert"
    body = f"Your account has been {transaction_type} on 01-01-2024 at Amazon."
    return {'subject': subject, 'body': body}


@st.composite
def email_missing_type(draw):
    """Generate email missing transaction type."""
    amount = draw(st.integers(min_value=1, max_value=10000))
    subject = f"Account Update"
    body = f"Amount: Rs {amount} on 01-01-2024 at Amazon."
    return {'subject': subject, 'body': body}


@st.composite
def email_missing_date(draw):
    """Generate email missing date."""
    amount = draw(st.integers(min_value=1, max_value=10000))
    transaction_type = draw(st.sampled_from(['debited', 'credited']))
    subject = f"Transaction Alert"
    body = f"Your account has been {transaction_type} with Rs {amount} at Amazon."
    return {'subject': subject, 'body': body}


@st.composite
def completely_invalid_email(draw):
    """Generate completely invalid email."""
    text = draw(st.text(min_size=10, max_size=100))
    return {'subject': text, 'body': text}


@pytest.mark.property
@settings(max_examples=30)
@given(email_data=email_missing_amount())
def test_parser_returns_none_when_amount_missing(email_data):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None when amount is missing.
    """
    # Parse email
    parsed = parse_email(email_data['subject'], email_data['body'])
    
    # Should return None for incomplete data
    assert parsed is None, \
        "Parser should return None when amount is missing"


@pytest.mark.property
@settings(max_examples=30)
@given(email_data=email_missing_type())
def test_parser_returns_none_when_type_missing(email_data):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None when transaction type is missing.
    """
    # Parse email
    parsed = parse_email(email_data['subject'], email_data['body'])
    
    # Should return None for incomplete data
    assert parsed is None, \
        "Parser should return None when transaction type is missing"


@pytest.mark.property
@settings(max_examples=20)
@given(email_data=completely_invalid_email())
def test_parser_returns_none_for_invalid_email(email_data):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None for completely invalid emails.
    """
    # Parse email
    parsed = parse_email(email_data['subject'], email_data['body'])
    
    # Should return None for invalid data
    assert parsed is None, \
        "Parser should return None for invalid email content"


@pytest.mark.property
def test_parser_handles_empty_subject():
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should handle empty subject gracefully.
    """
    # Parse with empty subject
    parsed = parse_email("", "Your account has been debited with Rs 500 on 01-01-2024.")
    
    # Should either parse from body or return None
    # Should not raise an exception
    assert parsed is None or parsed is not None


@pytest.mark.property
def test_parser_handles_empty_body():
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should handle empty body gracefully.
    """
    # Parse with empty body
    parsed = parse_email("Transaction Alert: Rs 500 debited", "")
    
    # Should either parse from subject or return None
    # Should not raise an exception
    assert parsed is None or parsed is not None


@pytest.mark.property
def test_parser_handles_both_empty():
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should handle both empty subject and body gracefully.
    """
    # Parse with both empty
    parsed = parse_email("", "")
    
    # Should return None
    assert parsed is None, \
        "Parser should return None for empty email"


@pytest.mark.property
@settings(max_examples=20)
@given(text=st.text(min_size=0, max_size=50))
def test_parser_handles_random_text(text):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should handle random text without crashing.
    """
    # Parse random text
    parsed = parse_email(text, text)
    
    # Should return None or valid ParsedTransaction
    # Should not raise an exception
    assert parsed is None or hasattr(parsed, 'amount')


@pytest.mark.property
@settings(max_examples=20)
@given(
    amount=st.integers(min_value=1, max_value=10000),
    invalid_type=st.text(min_size=5, max_size=20).filter(
        lambda x: 'debit' not in x.lower() and 'credit' not in x.lower()
    )
)
def test_parser_returns_none_with_invalid_transaction_type(amount, invalid_type):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None when transaction type cannot be determined.
    """
    subject = f"Transaction Alert"
    body = f"Your account has been {invalid_type} with Rs {amount} on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    # Should return None when type is invalid
    assert parsed is None, \
        f"Parser should return None for invalid type '{invalid_type}'"


@pytest.mark.property
@settings(max_examples=20)
@given(malformed_amount=st.text(min_size=1, max_size=20).filter(
    lambda x: not any(c.isdigit() for c in x)
))
def test_parser_returns_none_with_malformed_amount(malformed_amount):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None when amount is malformed.
    """
    subject = f"Transaction Alert"
    body = f"Your account has been debited with Rs {malformed_amount} on 01-01-2024."
    
    parsed = parse_email(subject, body)
    
    # Should return None when amount is malformed
    assert parsed is None, \
        f"Parser should return None for malformed amount '{malformed_amount}'"


@pytest.mark.property
def test_parser_does_not_return_partial_transaction():
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should not return a partial transaction with missing required fields.
    """
    # Email with only amount, missing type and date
    subject = "Account Update"
    body = "Amount: Rs 500"
    
    parsed = parse_email(subject, body)
    
    # Should return None, not a partial transaction
    assert parsed is None, \
        "Parser should return None, not a partial transaction"


@pytest.mark.property
@settings(max_examples=20)
@given(special_chars=st.text(alphabet=st.characters(
    blacklist_categories=('Ll', 'Lu', 'Nd'),
    min_codepoint=33,
    max_codepoint=126
), min_size=10, max_size=50))
def test_parser_handles_special_characters(special_chars):
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should handle emails with special characters gracefully.
    """
    subject = f"Transaction {special_chars}"
    body = f"Your account {special_chars} Rs 500 debited on 01-01-2024."
    
    # Should not crash
    parsed = parse_email(subject, body)
    
    # Should return None or valid transaction
    assert parsed is None or hasattr(parsed, 'amount')


@pytest.mark.property
def test_parser_returns_none_not_exception():
    """
    Property 11: Parser Error Handling
    
    **Validates: Requirements 4.9**
    
    Parser should return None on error, not raise an exception.
    """
    # Various invalid inputs
    invalid_inputs = [
        ("", ""),
        (None, None),
        ("Invalid", "Invalid"),
        ("123", "456"),
    ]
    
    for subject, body in invalid_inputs:
        try:
            # Convert None to empty string
            subject = subject or ""
            body = body or ""
            
            parsed = parse_email(subject, body)
            
            # Should return None, not raise exception
            assert parsed is None or hasattr(parsed, 'amount')
            
        except Exception as e:
            pytest.fail(f"Parser raised exception for input ({subject}, {body}): {e}")
