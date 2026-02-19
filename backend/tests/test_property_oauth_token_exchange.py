"""
Property-based test for OAuth token exchange.

Feature: gmail-expense-tracker
Property 2: OAuth Token Exchange

**Validates: Requirements 2.2**

For any valid OAuth authorization code, the token exchange process should 
return both an access token and a refresh token.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch

from app.auth.oauth import handle_oauth_callback, initiate_oauth_flow


# Strategy for generating authorization codes (simulating OAuth codes)
auth_code_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=20,
    max_size=100
)


@pytest.mark.property
def test_oauth_flow_generates_authorization_url():
    """
    Property 2: OAuth Token Exchange (Authorization URL generation)
    
    **Validates: Requirements 2.2**
    
    The OAuth flow should generate a valid authorization URL.
    """
    # Generate authorization URL
    auth_url = initiate_oauth_flow()
    
    # URL should be a non-empty string
    assert isinstance(auth_url, str), "Authorization URL should be a string"
    assert len(auth_url) > 0, "Authorization URL should not be empty"
    
    # URL should contain Google OAuth endpoint
    assert "accounts.google.com" in auth_url, \
        "Authorization URL should point to Google OAuth"
    
    # URL should contain required parameters
    assert "client_id" in auth_url, "URL should contain client_id parameter"
    assert "redirect_uri" in auth_url, "URL should contain redirect_uri parameter"
    assert "scope" in auth_url, "URL should contain scope parameter"
    assert "access_type=offline" in auth_url, \
        "URL should request offline access for refresh token"


@pytest.mark.property
@settings(max_examples=10)
@given(code=auth_code_strategy)
def test_oauth_callback_with_valid_code_returns_tokens(code):
    """
    Property 2: OAuth Token Exchange
    
    **Validates: Requirements 2.2**
    
    For any valid OAuth authorization code, the token exchange should return 
    both access and refresh tokens.
    
    Note: This test uses mocking since we can't make real OAuth calls.
    """
    # Mock the OAuth flow and credentials
    mock_credentials = Mock()
    mock_credentials.token = "mock_access_token_" + code[:10]
    mock_credentials.refresh_token = "mock_refresh_token_" + code[:10]
    mock_credentials.id_token = "mock_id_token"
    
    mock_flow = Mock()
    mock_flow.credentials = mock_credentials
    mock_flow.fetch_token = Mock()
    
    # Mock ID token verification
    mock_id_info = {
        "email": "test@example.com",
        "name": "Test User",
        "sub": "google_user_id_123"
    }
    
    with patch('app.auth.oauth.Flow.from_client_config', return_value=mock_flow), \
         patch('google.oauth2.id_token.verify_oauth2_token', return_value=mock_id_info):
        
        # Exchange code for tokens
        result = handle_oauth_callback(code)
        
        # Verify both tokens are present
        assert "access_token" in result, "Result should contain access_token"
        assert "refresh_token" in result, "Result should contain refresh_token"
        
        # Verify tokens are non-empty strings
        assert isinstance(result["access_token"], str), \
            "Access token should be a string"
        assert len(result["access_token"]) > 0, \
            "Access token should not be empty"
        
        assert isinstance(result["refresh_token"], str), \
            "Refresh token should be a string"
        assert len(result["refresh_token"]) > 0, \
            "Refresh token should not be empty"
        
        # Verify user info is present
        assert "email" in result, "Result should contain email"
        assert "name" in result, "Result should contain name"
        assert "google_id" in result, "Result should contain google_id"


@pytest.mark.property
def test_oauth_callback_with_empty_code_raises_error():
    """
    Property 2: OAuth Token Exchange (Error handling)
    
    **Validates: Requirements 2.2**
    
    Attempting to exchange an empty authorization code should raise ValueError.
    """
    with pytest.raises(ValueError, match="Authorization code cannot be empty"):
        handle_oauth_callback("")


@pytest.mark.property
@settings(max_examples=10)
@given(code=auth_code_strategy)
def test_oauth_callback_without_refresh_token_raises_error(code):
    """
    Property 2: OAuth Token Exchange (Missing refresh token)
    
    **Validates: Requirements 2.2**
    
    If the OAuth response doesn't include a refresh token, an error should be raised.
    """
    # Mock credentials without refresh token
    mock_credentials = Mock()
    mock_credentials.token = "mock_access_token"
    mock_credentials.refresh_token = None  # No refresh token
    
    mock_flow = Mock()
    mock_flow.credentials = mock_credentials
    mock_flow.fetch_token = Mock()
    
    with patch('app.auth.oauth.Flow.from_client_config', return_value=mock_flow):
        # Should raise error when refresh token is missing
        with pytest.raises(ValueError, match="No refresh token received"):
            handle_oauth_callback(code)


@pytest.mark.property
@settings(max_examples=10)
@given(code=auth_code_strategy)
def test_oauth_callback_with_invalid_code_raises_error(code):
    """
    Property 2: OAuth Token Exchange (Invalid code handling)
    
    **Validates: Requirements 2.2**
    
    If the authorization code is invalid, token exchange should raise an error.
    """
    # Mock flow that raises exception on fetch_token
    mock_flow = Mock()
    mock_flow.fetch_token = Mock(side_effect=Exception("Invalid authorization code"))
    
    with patch('app.auth.oauth.Flow.from_client_config', return_value=mock_flow):
        # Should raise error for invalid code
        with pytest.raises(ValueError, match="Token exchange failed"):
            handle_oauth_callback(code)


@pytest.mark.property
def test_oauth_flow_includes_required_scopes():
    """
    Property 2: OAuth Token Exchange (Scope verification)
    
    **Validates: Requirements 2.2**
    
    The OAuth authorization URL should include all required scopes.
    """
    auth_url = initiate_oauth_flow()
    
    # Required scopes
    required_scopes = [
        "gmail.readonly",
        "openid",
        "userinfo.email",
        "userinfo.profile"
    ]
    
    # Check that all required scopes are in the URL
    for scope in required_scopes:
        assert scope in auth_url, \
            f"Authorization URL should include scope: {scope}"
