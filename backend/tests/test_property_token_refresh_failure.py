"""
Property-based test for token refresh failure handling.

Feature: gmail-expense-tracker
Property 6: Token Refresh Failure Handling

**Validates: Requirements 2.7**

For any failed token refresh attempt (invalid or revoked refresh token), 
the system should return an authentication error and clear the session cookie.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch

from app.auth.oauth import refresh_access_token


# Strategy for generating refresh tokens
refresh_token_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=30,
    max_size=150
)


@pytest.mark.property
@settings(max_examples=30)
@given(refresh_token=refresh_token_strategy)
def test_revoked_refresh_token_raises_authentication_error(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    For any revoked refresh token, the refresh operation should raise an 
    authentication error.
    """
    # Mock credentials that fail with revoked token error
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(
        side_effect=Exception("Token has been expired or revoked")
    )
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise ValueError indicating authentication failure
        with pytest.raises(ValueError, match="Token refresh failed"):
            refresh_access_token(refresh_token)


@pytest.mark.property
@settings(max_examples=30)
@given(refresh_token=refresh_token_strategy)
def test_invalid_refresh_token_raises_authentication_error(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    For any invalid refresh token, the refresh operation should raise an 
    authentication error.
    """
    # Mock credentials that fail with invalid token error
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(
        side_effect=Exception("Invalid refresh token")
    )
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise ValueError indicating authentication failure
        with pytest.raises(ValueError, match="Token refresh failed"):
            refresh_access_token(refresh_token)


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_network_error_after_max_retries_raises_error(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    If token refresh fails after maximum retry attempts, an error should be raised.
    """
    from requests.exceptions import RequestException
    
    # Mock credentials that always fail with network error
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(
        side_effect=RequestException("Network error")
    )
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise error after retries are exhausted
        with pytest.raises((ValueError, RequestException)):
            refresh_access_token(refresh_token)


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_malformed_refresh_token_raises_error(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    For any malformed refresh token, the refresh operation should raise an error.
    """
    # Mock credentials that fail with malformed token error
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(
        side_effect=Exception("Malformed refresh token")
    )
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise ValueError
        with pytest.raises(ValueError, match="Token refresh failed"):
            refresh_access_token(refresh_token)


@pytest.mark.property
def test_none_refresh_token_raises_error():
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    Attempting to refresh with None as refresh token should raise an error.
    """
    with pytest.raises((ValueError, TypeError, AttributeError)):
        refresh_access_token(None)


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_refresh_failure_provides_clear_error_message(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    For any refresh failure, the error message should clearly indicate 
    the failure reason.
    """
    # Mock credentials that fail
    mock_credentials = Mock()
    error_message = "Specific error: token expired"
    mock_credentials.refresh = Mock(side_effect=Exception(error_message))
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise error with descriptive message
        with pytest.raises(ValueError) as exc_info:
            refresh_access_token(refresh_token)
        
        # Error message should contain context
        assert "Token refresh failed" in str(exc_info.value), \
            "Error message should indicate token refresh failure"


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_refresh_failure_does_not_expose_sensitive_data(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    For any refresh failure, the error should not expose the refresh token 
    or other sensitive data.
    """
    # Mock credentials that fail
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(side_effect=Exception("Token invalid"))
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise error
        with pytest.raises(ValueError) as exc_info:
            refresh_access_token(refresh_token)
        
        # Error message should not contain the refresh token
        error_message = str(exc_info.value)
        assert refresh_token not in error_message, \
            "Error message should not expose the refresh token"


@pytest.mark.property
@settings(max_examples=10)
@given(refresh_token=refresh_token_strategy)
def test_consecutive_refresh_failures_all_raise_errors(refresh_token):
    """
    Property 6: Token Refresh Failure Handling
    
    **Validates: Requirements 2.7**
    
    Multiple consecutive refresh attempts with an invalid token should all fail.
    """
    # Mock credentials that always fail
    mock_credentials = Mock()
    mock_credentials.refresh = Mock(side_effect=Exception("Invalid token"))
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # First attempt should fail
        with pytest.raises(ValueError):
            refresh_access_token(refresh_token)
        
        # Second attempt should also fail
        with pytest.raises(ValueError):
            refresh_access_token(refresh_token)
        
        # Third attempt should also fail
        with pytest.raises(ValueError):
            refresh_access_token(refresh_token)
