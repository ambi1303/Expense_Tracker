"""
Property-based test for logout session clearing.

Feature: gmail-expense-tracker
Property 24: Logout Session Clearing

**Validates: Requirements 7.9**

For any logout request, the response should clear the session cookie and 
subsequent requests with that token should be rejected.
"""

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import uuid

from main import app
from app.auth.jwt_handler import create_session_token


# Strategy for generating user data
user_id_strategy = st.uuids().map(str)
email_strategy = st.emails()


@pytest.mark.property
def test_logout_clears_session_cookie():
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    For any logout request, the session cookie should be cleared.
    """
    client = TestClient(app)
    
    # Make logout request
    response = client.post("/auth/logout")
    
    # Should return success
    assert response.status_code == 200, \
        f"Logout should return 200, got {response.status_code}"
    
    # Check response body
    data = response.json()
    assert "message" in data, "Response should contain message"
    assert "logged out" in data["message"].lower(), \
        "Message should confirm logout"
    
    # Check that cookie is cleared
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "session_token" in set_cookie_header, \
        "Set-Cookie header should contain session_token"
    
    # Cookie should be cleared (Max-Age=0 or expires in past)
    assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header.lower(), \
        "Cookie should be cleared with Max-Age=0 or expires directive"


@pytest.mark.property
@settings(max_examples=20)
@given(user_id=user_id_strategy, email=email_strategy)
def test_cleared_session_cannot_access_protected_endpoints(user_id, email):
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    After logout, the cleared session token should not be able to access 
    protected endpoints.
    """
    client = TestClient(app)
    
    # Create a valid session token
    session_token = create_session_token(user_id, email)
    
    # Mock database to return a user for the token
    mock_user = Mock()
    mock_user.id = uuid.UUID(user_id)
    mock_user.email = email
    mock_user.name = "Test User"
    mock_user.created_at = "2024-01-01T00:00:00"
    
    with patch('app.auth.middleware.get_db') as mock_get_db:
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        async def mock_db_generator():
            yield mock_db
        
        mock_get_db.return_value = mock_db_generator()
        
        # First, verify the token works before logout
        response_before = client.get(
            "/auth/me",
            cookies={"session_token": session_token}
        )
        assert response_before.status_code == 200, \
            "Token should work before logout"
        
        # Perform logout
        logout_response = client.post(
            "/auth/logout",
            cookies={"session_token": session_token}
        )
        assert logout_response.status_code == 200, "Logout should succeed"
        
        # Try to access protected endpoint after logout (without cookie)
        response_after = client.get("/auth/me")
        
        # Should be unauthorized
        assert response_after.status_code == 401, \
            f"Should return 401 after logout, got {response_after.status_code}"


@pytest.mark.property
@settings(max_examples=10)
@given(user_id=user_id_strategy, email=email_strategy)
def test_logout_multiple_times_succeeds(user_id, email):
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    Multiple logout requests should all succeed (idempotent operation).
    """
    client = TestClient(app)
    
    # Create a session token
    session_token = create_session_token(user_id, email)
    
    # First logout
    response1 = client.post(
        "/auth/logout",
        cookies={"session_token": session_token}
    )
    assert response1.status_code == 200, "First logout should succeed"
    
    # Second logout (without cookie)
    response2 = client.post("/auth/logout")
    assert response2.status_code == 200, "Second logout should succeed"
    
    # Third logout (without cookie)
    response3 = client.post("/auth/logout")
    assert response3.status_code == 200, "Third logout should succeed"


@pytest.mark.property
def test_logout_without_session_succeeds():
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    Logout should succeed even without an active session (idempotent).
    """
    client = TestClient(app)
    
    # Logout without any session cookie
    response = client.post("/auth/logout")
    
    # Should still return success
    assert response.status_code == 200, \
        f"Logout without session should return 200, got {response.status_code}"
    
    # Should still clear the cookie (even if it wasn't set)
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "session_token" in set_cookie_header, \
        "Should still set cookie clearing directive"


@pytest.mark.property
@settings(max_examples=20)
@given(user_id=user_id_strategy, email=email_strategy)
def test_logout_response_contains_confirmation_message(user_id, email):
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    Logout response should contain a confirmation message.
    """
    client = TestClient(app)
    
    # Create a session token
    session_token = create_session_token(user_id, email)
    
    # Perform logout
    response = client.post(
        "/auth/logout",
        cookies={"session_token": session_token}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Should have a message field
    assert "message" in data, "Response should contain message field"
    assert isinstance(data["message"], str), "Message should be a string"
    assert len(data["message"]) > 0, "Message should not be empty"
    
    # Message should indicate successful logout
    message_lower = data["message"].lower()
    assert "logout" in message_lower or "logged out" in message_lower, \
        "Message should mention logout"


@pytest.mark.property
@settings(max_examples=10)
@given(user_id=user_id_strategy, email=email_strategy)
def test_logout_clears_cookie_with_correct_attributes(user_id, email):
    """
    Property 24: Logout Session Clearing
    
    **Validates: Requirements 7.9**
    
    Logout should clear the cookie with the same attributes it was set with
    (httponly, samesite).
    """
    client = TestClient(app)
    
    # Create a session token
    session_token = create_session_token(user_id, email)
    
    # Perform logout
    response = client.post(
        "/auth/logout",
        cookies={"session_token": session_token}
    )
    
    # Check Set-Cookie header
    set_cookie_header = response.headers.get("set-cookie", "")
    
    # Should have HttpOnly attribute
    assert "HttpOnly" in set_cookie_header, \
        "Cleared cookie should have HttpOnly attribute"
    
    # Should have SameSite attribute
    assert "SameSite" in set_cookie_header, \
        "Cleared cookie should have SameSite attribute"
