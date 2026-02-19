"""
Unit tests for authentication routes.

Tests the authentication endpoints including OAuth flow, callback handling,
user profile retrieval, and logout functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import uuid

from main import app


client = TestClient(app)


def test_google_auth_redirects_to_oauth():
    """
    Test OAuth URL generation contains correct scopes.
    
    **Validates: Requirements 2.1**
    """
    # Make request to initiate OAuth
    response = client.get("/auth/google", follow_redirects=False)
    
    # Should redirect
    assert response.status_code in [302, 307], \
        f"Expected redirect, got {response.status_code}"
    
    # Get redirect URL
    redirect_url = response.headers.get("location", "")
    
    # Should redirect to Google OAuth
    assert "accounts.google.com" in redirect_url, \
        "Should redirect to Google OAuth"
    
    # Check for required scopes
    assert "gmail.readonly" in redirect_url, \
        "Should request gmail.readonly scope"
    assert "openid" in redirect_url, \
        "Should request openid scope"
    assert "userinfo.email" in redirect_url, \
        "Should request userinfo.email scope"
    assert "userinfo.profile" in redirect_url, \
        "Should request userinfo.profile scope"


def test_callback_with_valid_code_creates_user_and_sets_cookie():
    """
    Test callback with valid code creates user and sets cookie.
    
    **Validates: Requirements 2.2, 2.4, 2.5**
    """
    # Mock OAuth callback handler
    mock_oauth_result = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "email": "newuser@example.com",
        "name": "New User",
        "google_id": "google_123456"
    }
    
    with patch('app.routes.auth.handle_oauth_callback', return_value=mock_oauth_result), \
         patch('app.routes.auth.encrypt_refresh_token', return_value="encrypted_token"), \
         patch('app.routes.auth.create_session_token', return_value="mock_jwt_token"), \
         patch('app.routes.auth.get_db') as mock_get_db:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # New user
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        
        async def mock_db_generator():
            yield mock_db
        
        mock_get_db.return_value = mock_db_generator()
        
        # Make callback request
        response = client.get("/auth/callback?code=valid_code", follow_redirects=False)
        
        # Should redirect to frontend
        assert response.status_code in [302, 307]
        
        # Should set session cookie
        assert "session_token" in response.cookies
        
        # Verify database operations were called
        assert mock_db.add.called or mock_db.commit.called


def test_auth_me_with_valid_token_returns_user():
    """
    Test /auth/me with valid token returns user.
    
    **Validates: Requirements 2.4**
    """
    # Create a mock user
    mock_user = Mock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"
    mock_user.created_at = "2024-01-01T00:00:00"
    
    # Mock the get_current_user dependency
    with patch('app.routes.auth.get_current_user', return_value=mock_user):
        # Make request with mock authentication
        response = client.get("/auth/me")
        
        # Should return user data
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"


def test_auth_me_with_invalid_token_returns_401():
    """
    Test /auth/me with invalid token returns 401.
    
    **Validates: Requirements 7.4**
    """
    # Make request without authentication
    response = client.get("/auth/me")
    
    # Should return 401 Unauthorized
    assert response.status_code == 401
    
    # Should have error detail
    data = response.json()
    assert "detail" in data


def test_logout_clears_cookie():
    """
    Test logout clears cookie.
    
    **Validates: Requirements 7.9**
    """
    # Make logout request
    response = client.post("/auth/logout")
    
    # Should return success
    assert response.status_code == 200
    
    # Should have success message
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()
    
    # Should clear cookie
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "session_token" in set_cookie_header
    assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header.lower()


def test_callback_with_existing_user_updates_token():
    """
    Test callback with existing user updates refresh token.
    
    **Validates: Requirements 2.2, 2.3**
    """
    # Mock OAuth callback handler
    mock_oauth_result = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "email": "existing@example.com",
        "name": "Existing User",
        "google_id": "google_existing"
    }
    
    # Mock existing user
    mock_user = Mock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "existing@example.com"
    mock_user.name = "Existing User"
    mock_user.google_id = "google_existing"
    mock_user.refresh_token_encrypted = "old_encrypted_token"
    
    with patch('app.routes.auth.handle_oauth_callback', return_value=mock_oauth_result), \
         patch('app.routes.auth.encrypt_refresh_token', return_value="new_encrypted_token"), \
         patch('app.routes.auth.create_session_token', return_value="mock_jwt_token"), \
         patch('app.routes.auth.get_db') as mock_get_db:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user  # Existing user
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        
        async def mock_db_generator():
            yield mock_db
        
        mock_get_db.return_value = mock_db_generator()
        
        # Make callback request
        response = client.get("/auth/callback?code=valid_code", follow_redirects=False)
        
        # Should redirect
        assert response.status_code in [302, 307]
        
        # User's refresh token should be updated
        assert mock_user.refresh_token_encrypted == "new_encrypted_token"


def test_callback_without_code_returns_error():
    """
    Test callback without authorization code returns error.
    
    **Validates: Requirements 2.2**
    """
    # Make callback request without code
    response = client.get("/auth/callback")
    
    # Should return error (422 for missing parameter)
    assert response.status_code == 422


def test_callback_with_invalid_code_returns_error():
    """
    Test callback with invalid code returns error.
    
    **Validates: Requirements 2.2**
    """
    # Mock OAuth callback to raise error
    with patch('app.routes.auth.handle_oauth_callback', side_effect=ValueError("Invalid code")):
        # Make callback request
        response = client.get("/auth/callback?code=invalid_code", follow_redirects=False)
        
        # Should return error
        assert response.status_code == 400
        
        # Should have error detail
        data = response.json()
        assert "detail" in data


def test_auth_me_without_cookie_returns_401():
    """
    Test /auth/me without session cookie returns 401.
    
    **Validates: Requirements 7.4**
    """
    # Make request without cookie
    response = client.get("/auth/me")
    
    # Should return 401
    assert response.status_code == 401
    
    # Should have authentication error
    data = response.json()
    assert "detail" in data
    assert "authenticated" in data["detail"].lower() or "token" in data["detail"].lower()


def test_logout_is_idempotent():
    """
    Test logout can be called multiple times.
    
    **Validates: Requirements 7.9**
    """
    # First logout
    response1 = client.post("/auth/logout")
    assert response1.status_code == 200
    
    # Second logout
    response2 = client.post("/auth/logout")
    assert response2.status_code == 200
    
    # Both should succeed
    assert response1.json()["message"] == response2.json()["message"]
