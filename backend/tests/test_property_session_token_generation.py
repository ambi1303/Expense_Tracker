"""
Property-based test for session token generation.

Feature: gmail-expense-tracker
Property 4: Session Token Generation

**Validates: Requirements 2.4, 2.5**

For any successful authentication, a JWT session token should be generated 
and included in the response as an HTTPOnly secure cookie.
"""

import pytest
from hypothesis import given, strategies as st, settings
from jose import jwt, JWTError
from datetime import datetime, timezone

from app.auth.jwt_handler import create_session_token, verify_session_token, get_jwt_config


# Strategy for generating user IDs (UUIDs as strings)
user_id_strategy = st.uuids().map(str)

# Strategy for generating email addresses
email_strategy = st.emails()


@pytest.mark.property
@settings(max_examples=50)
@given(user_id=user_id_strategy, email=email_strategy)
def test_session_token_generation_creates_valid_jwt(user_id, email):
    """
    Property 4: Session Token Generation
    
    **Validates: Requirements 2.4, 2.5**
    
    For any user_id and email, a valid JWT token should be generated.
    """
    # Create session token
    token = create_session_token(user_id, email)
    
    # Token should be a non-empty string
    assert isinstance(token, str), "Token should be a string"
    assert len(token) > 0, "Token should not be empty"
    
    # Token should be a valid JWT (has 3 parts separated by dots)
    parts = token.split('.')
    assert len(parts) == 3, f"JWT should have 3 parts, got {len(parts)}"


@pytest.mark.property
@settings(max_examples=50)
@given(user_id=user_id_strategy, email=email_strategy)
def test_session_token_contains_correct_payload(user_id, email):
    """
    Property 4: Session Token Generation (Payload verification)
    
    **Validates: Requirements 2.4, 2.5**
    
    For any user_id and email, the generated token should contain the correct payload.
    """
    # Create session token
    token = create_session_token(user_id, email)
    
    # Decode without verification to check payload
    config = get_jwt_config()
    payload = jwt.decode(token, config["secret"], algorithms=[config["algorithm"]])
    
    # Verify payload contains correct user information
    assert payload["sub"] == user_id, f"Token subject should be {user_id}"
    assert payload["email"] == email, f"Token email should be {email}"
    
    # Verify token has expiration and issued-at times
    assert "exp" in payload, "Token should have expiration time"
    assert "iat" in payload, "Token should have issued-at time"
    
    # Verify expiration is in the future
    exp_timestamp = payload["exp"]
    assert exp_timestamp > datetime.now(timezone.utc).timestamp(), \
        "Token expiration should be in the future"


@pytest.mark.property
@settings(max_examples=50)
@given(user_id=user_id_strategy, email=email_strategy)
def test_session_token_verification_roundtrip(user_id, email):
    """
    Property 4: Session Token Generation (Verification roundtrip)
    
    **Validates: Requirements 2.4, 2.5**
    
    For any user_id and email, creating and verifying a token should return 
    the original user information.
    """
    # Create session token
    token = create_session_token(user_id, email)
    
    # Verify the token
    verified_data = verify_session_token(token)
    
    # Verify the data matches
    assert verified_data["user_id"] == user_id, \
        f"Verified user_id should match. Expected: {user_id}, Got: {verified_data['user_id']}"
    assert verified_data["email"] == email, \
        f"Verified email should match. Expected: {email}, Got: {verified_data['email']}"


@pytest.mark.property
@settings(max_examples=50)
@given(user_id1=user_id_strategy, email1=email_strategy, 
       user_id2=user_id_strategy, email2=email_strategy)
def test_different_users_produce_different_tokens(user_id1, email1, user_id2, email2):
    """
    Property 4: Session Token Generation (Uniqueness)
    
    **Validates: Requirements 2.4, 2.5**
    
    For any two different users, their session tokens should be different.
    """
    # Skip if users are the same
    if user_id1 == user_id2 and email1 == email2:
        return
    
    # Create tokens for both users
    token1 = create_session_token(user_id1, email1)
    token2 = create_session_token(user_id2, email2)
    
    # Tokens should be different
    assert token1 != token2, \
        "Different users should produce different tokens"


@pytest.mark.property
def test_empty_user_id_raises_error():
    """
    Property 4: Session Token Generation (Error handling)
    
    **Validates: Requirements 2.4, 2.5**
    
    Attempting to create a token with empty user_id should raise ValueError.
    """
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        create_session_token("", "test@example.com")


@pytest.mark.property
def test_empty_email_raises_error():
    """
    Property 4: Session Token Generation (Error handling)
    
    **Validates: Requirements 2.4, 2.5**
    
    Attempting to create a token with empty email should raise ValueError.
    """
    with pytest.raises(ValueError, match="email cannot be empty"):
        create_session_token("user123", "")


@pytest.mark.property
def test_invalid_token_verification_fails():
    """
    Property 4: Session Token Generation (Invalid token handling)
    
    **Validates: Requirements 2.4, 2.5**
    
    Attempting to verify an invalid token should raise JWTError.
    """
    with pytest.raises(JWTError):
        verify_session_token("invalid.token.here")


@pytest.mark.property
def test_empty_token_verification_raises_error():
    """
    Property 4: Session Token Generation (Empty token handling)
    
    **Validates: Requirements 2.4, 2.5**
    
    Attempting to verify an empty token should raise ValueError.
    """
    with pytest.raises(ValueError, match="token cannot be empty"):
        verify_session_token("")
