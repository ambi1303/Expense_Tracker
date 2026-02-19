"""
Property-based test for HTTPOnly cookie setting.

Feature: gmail-expense-tracker
Property 4: Session Token Generation (Cookie attributes)

**Validates: Requirements 2.5**

For any successful authentication, a JWT session token should be included 
in the response as an HTTPOnly secure cookie.
"""

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import uuid

from main import app


# Strategy for generating OAuth codes
oauth_code_strategy = st.text(
    alphabet=st.characters(min_codepoint=48, max_codepoint=122, 
                          blacklist_categories=('Cc', 'Cs')),
    min_size=20,
    max_size=100
)


@pytest.mark.property
@settings(max_examples=20)
@given(code=oauth_code_strategy)
def test_oauth_callback_sets_httponly_cookie(code):
    """
    Property 4: Session Token Generation (HTTPOnly cookie)
    
    **Validates: Requirements 2.5**
    
    For any successful OAuth callback, the response should set an HTTPOnly 
    session cookie.
    """
    client = TestClient(app)
    
    # Mock OAuth callback handler
    mock_oauth_result = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "email": "test@example.com",
        "name": "Test User",
        "google_id": str(uuid.uuid4())
    }
    
    # Mock database operations
    mock_user = Mock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"
    mock_user.created_at = "2024-01-01T00:00:00"
    
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
        
        # Make request to callback endpoint
        response = client.get(f"/auth/callback?code={code}", follow_redirects=False)
        
        # Should redirect (302 or 307)
        assert response.status_code in [302, 307], \
            f"Expected redirect status code, got {response.status_code}"
        
        # Check that session_token cookie is set
        assert "session_token" in response.cookies, \
            "Response should set session_token cookie"
        
        # Get cookie details
        cookie = response.cookies.get("session_token")
        assert cookie is not None, "session_token cookie should not be None"


@pytest.mark.property
@settings(max_examples=20)
@given(code=oauth_code_strategy)
def test_session_cookie_has_httponly_attribute(code):
    """
    Property 4: Session Token Generation (HTTPOnly attribute)
    
    **Validates: Requirements 2.5**
    
    The session cookie should have the HTTPOnly attribute set to prevent 
    JavaScript access.
    """
    client = TestClient(app)
    
    # Mock OAuth callback handler
    mock_oauth_result = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "email": "test@example.com",
        "name": "Test User",
        "google_id": str(uuid.uuid4())
    }
    
    with patch('app.routes.auth.handle_oauth_callback', return_value=mock_oauth_result), \
         patch('app.routes.auth.encrypt_refresh_token', return_value="encrypted_token"), \
         patch('app.routes.auth.create_session_token', return_value="mock_jwt_token"), \
         patch('app.routes.auth.get_db') as mock_get_db:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        
        async def mock_db_generator():
            yield mock_db
        
        mock_get_db.return_value = mock_db_generator()
        
        # Make request
        response = client.get(f"/auth/callback?code={code}", follow_redirects=False)
        
        # Check Set-Cookie header for HTTPOnly attribute
        set_cookie_header = response.headers.get("set-cookie", "")
        
        assert "session_token" in set_cookie_header, \
            "Set-Cookie header should contain session_token"
        assert "HttpOnly" in set_cookie_header, \
            "Cookie should have HttpOnly attribute"


@pytest.mark.property
@settings(max_examples=20)
@given(code=oauth_code_strategy)
def test_session_cookie_has_samesite_attribute(code):
    """
    Property 4: Session Token Generation (SameSite attribute)
    
    **Validates: Requirements 2.5**
    
    The session cookie should have the SameSite attribute for CSRF protection.
    """
    client = TestClient(app)
    
    # Mock OAuth callback handler
    mock_oauth_result = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "email": "test@example.com",
        "name": "Test User",
        "google_id": str(uuid.uuid4())
    }
    
    with patch('app.routes.auth.handle_oauth_callback', return_value=mock_oauth_result), \
         patch('app.routes.auth.encrypt_refresh_token', return_value="encrypted_token"), \
         patch('app.routes.auth.create_session_token', return_value="mock_jwt_token"), \
         patch('app.routes.auth.get_db') as mock_get_db:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.refresh = AsyncMock()
        
        async def mock_db_generator():
            yield mock_db
        
        mock_get_db.return_value = mock_db_generator()
        
        # Make request
        response = client.get(f"/auth/callback?code={code}", follow_redirects=False)
        
        # Check Set-Cookie header for SameSite attribute
        set_cookie_header = response.headers.get("set-cookie", "")
        
        assert "SameSite" in set_cookie_header, \
            "Cookie should have SameSite attribute"


@pytest.mark.property
def test_logout_clears_session_cookie():
    """
    Property 4: Session Token Generation (Cookie clearing on logout)
    
    **Validates: Requirements 2.5**
    
    Logout should clear the session cookie.
    """
    client = TestClient(app)
    
    # Make logout request
    response = client.post("/auth/logout")
    
    # Should return success
    assert response.status_code == 200
    
    # Check that cookie is cleared (max-age=0 or expires in past)
    set_cookie_header = response.headers.get("set-cookie", "")
    
    # Cookie should be present in header (being cleared)
    assert "session_token" in set_cookie_header, \
        "Set-Cookie header should contain session_token"
    
    # Should have max-age=0 or expires directive to clear it
    assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header.lower(), \
        "Cookie should be cleared with Max-Age=0 or expires directive"
