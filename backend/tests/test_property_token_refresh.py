"""
Property-based test for token refresh on expiration.

Feature: gmail-expense-tracker
Property 5: Token Refresh on Expiration

**Validates: Requirements 2.6**

For any expired access token with a valid refresh token, the system should 
successfully obtain a new access token without user intervention.
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
def test_valid_refresh_token_returns_new_access_token(refresh_token):
    """
    Property 5: Token Refresh on Expiration
    
    **Validates: Requirements 2.6**
    
    For any valid refresh token, the refresh operation should return a new 
    access token.
    
    Note: This test uses mocking since we can't make real OAuth calls.
    """
    # Mock credentials with successful refresh
    mock_credentials = Mock()
    mock_credentials.token = "new_access_token_" + refresh_token[:10]
    mock_credentials.refresh = Mock()
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Refresh the token
        new_access_token = refresh_access_token(refresh_token)
        
        # Should return a non-empty access token
        assert isinstance(new_access_token, str), \
            "New access token should be a string"
        assert len(new_access_token) > 0, \
            "New access token should not be empty"
        
        # Verify refresh was called
        mock_credentials.refresh.assert_called_once()


@pytest.mark.property
@settings(max_examples=30)
@given(token1=refresh_token_strategy, token2=refresh_token_strategy)
def test_different_refresh_tokens_produce_different_access_tokens(token1, token2):
    """
    Property 5: Token Refresh on Expiration (Uniqueness)
    
    **Validates: Requirements 2.6**
    
    For any two different refresh tokens, the resulting access tokens should 
    be different.
    """
    # Skip if tokens are the same
    if token1 == token2:
        return
    
    # Mock credentials for first token
    mock_credentials1 = Mock()
    mock_credentials1.token = "access_token_1_" + token1[:10]
    mock_credentials1.refresh = Mock()
    
    # Mock credentials for second token
    mock_credentials2 = Mock()
    mock_credentials2.token = "access_token_2_" + token2[:10]
    mock_credentials2.refresh = Mock()
    
    with patch('app.auth.oauth.Credentials') as mock_creds_class:
        # First refresh
        mock_creds_class.return_value = mock_credentials1
        access_token1 = refresh_access_token(token1)
        
        # Second refresh
        mock_creds_class.return_value = mock_credentials2
        access_token2 = refresh_access_token(token2)
        
        # Access tokens should be different
        assert access_token1 != access_token2, \
            "Different refresh tokens should produce different access tokens"


@pytest.mark.property
def test_empty_refresh_token_raises_error():
    """
    Property 5: Token Refresh on Expiration (Error handling)
    
    **Validates: Requirements 2.6**
    
    Attempting to refresh with an empty refresh token should raise ValueError.
    """
    with pytest.raises(ValueError, match="Refresh token cannot be empty"):
        refresh_access_token("")


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_invalid_refresh_token_raises_error(refresh_token):
    """
    Property 5: Token Refresh on Expiration (Invalid token handling)
    
    **Validates: Requirements 2.6**
    
    If the refresh token is invalid or revoked, refresh should raise an error.
    """
    # Mock credentials that fail to refresh
    mock_credentials = Mock()
    mock_credentials.token = None  # No new token
    mock_credentials.refresh = Mock(side_effect=Exception("Invalid refresh token"))
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise error for invalid refresh token
        with pytest.raises(ValueError, match="Token refresh failed"):
            refresh_access_token(refresh_token)


@pytest.mark.property
@settings(max_examples=20)
@given(refresh_token=refresh_token_strategy)
def test_refresh_token_returns_none_raises_error(refresh_token):
    """
    Property 5: Token Refresh on Expiration (No token returned)
    
    **Validates: Requirements 2.6**
    
    If the refresh operation doesn't return a new access token, an error 
    should be raised.
    """
    # Mock credentials that refresh but don't return a token
    mock_credentials = Mock()
    mock_credentials.token = None  # No token after refresh
    mock_credentials.refresh = Mock()  # Refresh succeeds but no token
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should raise error when no token is returned
        with pytest.raises(ValueError, match="Failed to obtain new access token"):
            refresh_access_token(refresh_token)


@pytest.mark.property
@settings(max_examples=10)
@given(refresh_token=refresh_token_strategy)
def test_token_refresh_retries_on_network_error(refresh_token):
    """
    Property 5: Token Refresh on Expiration (Retry logic)
    
    **Validates: Requirements 2.6**
    
    Token refresh should retry on transient network errors.
    
    Note: This test verifies the retry decorator is applied.
    """
    from requests.exceptions import RequestException
    
    # Mock credentials that fail twice then succeed
    mock_credentials = Mock()
    mock_credentials.token = "new_access_token_after_retry"
    
    call_count = [0]
    
    def mock_refresh(request):
        call_count[0] += 1
        if call_count[0] < 3:
            raise RequestException("Network error")
        # Third call succeeds
        mock_credentials.token = "new_access_token_after_retry"
    
    mock_credentials.refresh = mock_refresh
    
    with patch('app.auth.oauth.Credentials', return_value=mock_credentials):
        # Should succeed after retries
        new_token = refresh_access_token(refresh_token)
        
        # Should have retried and eventually succeeded
        assert call_count[0] == 3, "Should have retried twice before succeeding"
        assert new_token == "new_access_token_after_retry"
