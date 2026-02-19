"""
Property-based test for JWT validation on protected endpoints.

Feature: gmail-expense-tracker
Property 20: JWT Validation on Protected Endpoints

**Validates: Requirements 7.4**

For any request to a protected endpoint with an invalid or missing JWT token, 
the system should return a 401 Unauthorized response.
"""

import pytest
from hypothesis import given, strategies as st, settings
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

from app.auth.jwt_handler import create_session_token, verify_session_token, get_jwt_config


# Strategy for generating user IDs
user_id_strategy = st.uuids().map(str)

# Strategy for generating email addresses
email_strategy = st.emails()

# Strategy for generating invalid tokens
invalid_token_strategy = st.one_of(
    st.just(""),  # Empty token
    st.just("invalid"),  # Single part
    st.just("invalid.token"),  # Two parts
    st.just("invalid.token.format"),  # Three parts but invalid
    st.text(min_size=1, max_size=50).filter(lambda x: '.' not in x),  # No dots
)


@pytest.mark.property
@settings(max_examples=50)
@given(user_id=user_id_strategy, email=email_strategy)
def test_valid_token_passes_validation(user_id, email):
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    For any valid JWT token, verification should succeed and return user data.
    """
    # Create a valid token
    token = create_session_token(user_id, email)
    
    # Verification should succeed
    verified_data = verify_session_token(token)
    
    # Should return correct user data
    assert verified_data["user_id"] == user_id
    assert verified_data["email"] == email


@pytest.mark.property
@settings(max_examples=30)
@given(invalid_token=invalid_token_strategy)
def test_invalid_token_fails_validation(invalid_token):
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    For any invalid JWT token, verification should fail with an error.
    """
    # Skip empty tokens as they raise ValueError, not JWTError
    if invalid_token == "":
        with pytest.raises(ValueError):
            verify_session_token(invalid_token)
    else:
        # Invalid tokens should raise JWTError
        with pytest.raises(JWTError):
            verify_session_token(invalid_token)


@pytest.mark.property
@settings(max_examples=20)
@given(user_id=user_id_strategy, email=email_strategy)
def test_expired_token_fails_validation(user_id, email):
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    For any expired JWT token, verification should fail.
    """
    config = get_jwt_config()
    
    # Create an expired token (expired 1 hour ago)
    expiration = datetime.now(timezone.utc) - timedelta(hours=1)
    
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.now(timezone.utc) - timedelta(hours=2)
    }
    
    expired_token = jwt.encode(payload, config["secret"], algorithm=config["algorithm"])
    
    # Verification should fail for expired token
    with pytest.raises(JWTError):
        verify_session_token(expired_token)


@pytest.mark.property
@settings(max_examples=20)
@given(user_id=user_id_strategy, email=email_strategy)
def test_token_with_wrong_signature_fails_validation(user_id, email):
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    For any JWT token signed with a different secret, verification should fail.
    """
    config = get_jwt_config()
    
    # Create a token with a different secret
    wrong_secret = "wrong_secret_key_that_is_different"
    
    expiration = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    
    # Sign with wrong secret
    token_with_wrong_signature = jwt.encode(
        payload, 
        wrong_secret, 
        algorithm=config["algorithm"]
    )
    
    # Verification should fail
    with pytest.raises(JWTError):
        verify_session_token(token_with_wrong_signature)


@pytest.mark.property
@settings(max_examples=20)
@given(user_id=user_id_strategy, email=email_strategy)
def test_token_missing_required_fields_fails_validation(user_id, email):
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    For any JWT token missing required fields (sub or email), 
    verification should fail.
    """
    config = get_jwt_config()
    
    # Create token missing 'sub' field
    expiration = datetime.now(timezone.utc) + timedelta(days=7)
    payload_missing_sub = {
        "email": email,
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    
    token_missing_sub = jwt.encode(
        payload_missing_sub, 
        config["secret"], 
        algorithm=config["algorithm"]
    )
    
    # Verification should fail
    with pytest.raises(JWTError):
        verify_session_token(token_missing_sub)
    
    # Create token missing 'email' field
    payload_missing_email = {
        "sub": user_id,
        "exp": expiration,
        "iat": datetime.now(timezone.utc)
    }
    
    token_missing_email = jwt.encode(
        payload_missing_email, 
        config["secret"], 
        algorithm=config["algorithm"]
    )
    
    # Verification should fail
    with pytest.raises(JWTError):
        verify_session_token(token_missing_email)


@pytest.mark.property
def test_none_token_fails_validation():
    """
    Property 20: JWT Validation on Protected Endpoints
    
    **Validates: Requirements 7.4**
    
    Attempting to verify None as a token should raise an error.
    """
    with pytest.raises((ValueError, TypeError, AttributeError)):
        verify_session_token(None)
