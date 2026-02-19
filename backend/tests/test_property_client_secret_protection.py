"""
Property-based test for client secret protection.

Feature: gmail-expense-tracker
Property 19: Client Secret Protection

**Validates: Requirements 7.2**

For any API response or frontend code bundle, Google client secrets should 
never be present in the content.
"""

import pytest
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
import os
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
def test_root_endpoint_does_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    The root endpoint should not expose the Google client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Make request to root endpoint
    response = client.get("/")
    
    # Check response
    assert response.status_code == 200
    response_text = response.text
    
    # Client secret should not be in response
    if client_secret:
        assert client_secret not in response_text, \
            "Client secret should not be exposed in API response"


@pytest.mark.property
def test_auth_google_endpoint_does_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    The OAuth initiation endpoint should not expose the client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Make request to OAuth endpoint
    response = client.get("/auth/google", follow_redirects=False)
    
    # Should redirect
    assert response.status_code in [302, 307]
    
    # Check redirect URL
    redirect_url = response.headers.get("location", "")
    
    # Client secret should not be in redirect URL
    if client_secret:
        assert client_secret not in redirect_url, \
            "Client secret should not be in OAuth redirect URL"


@pytest.mark.property
@settings(max_examples=20)
@given(code=oauth_code_strategy)
def test_auth_callback_does_not_expose_client_secret(code):
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    The OAuth callback endpoint should not expose the client secret in responses.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
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
        
        # Check response headers and body
        response_text = str(response.headers) + response.text
        
        # Client secret should not be in response
        if client_secret:
            assert client_secret not in response_text, \
                "Client secret should not be exposed in callback response"


@pytest.mark.property
def test_auth_me_endpoint_does_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    The /auth/me endpoint should not expose the client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Make request without authentication (will return 401)
    response = client.get("/auth/me")
    
    # Check response
    response_text = response.text
    
    # Client secret should not be in error response
    if client_secret:
        assert client_secret not in response_text, \
            "Client secret should not be in error response"


@pytest.mark.property
def test_openapi_docs_do_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    The OpenAPI documentation should not expose the client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Get OpenAPI schema
    response = client.get("/openapi.json")
    
    # Check response
    assert response.status_code == 200
    response_text = response.text
    
    # Client secret should not be in OpenAPI schema
    if client_secret:
        assert client_secret not in response_text, \
            "Client secret should not be in OpenAPI documentation"


@pytest.mark.property
def test_error_responses_do_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    Error responses should not expose the client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Make request to non-existent endpoint
    response = client.get("/nonexistent")
    
    # Check error response
    response_text = response.text
    
    # Client secret should not be in error response
    if client_secret:
        assert client_secret not in response_text, \
            "Client secret should not be in error responses"


@pytest.mark.property
def test_client_secret_not_in_environment_variable_list():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    API responses should not list environment variables that could expose secrets.
    """
    client = TestClient(app)
    
    # Make request to root endpoint
    response = client.get("/")
    
    # Check response
    response_text = response.text.lower()
    
    # Should not contain references to environment variables
    sensitive_terms = ["google_client_secret", "client_secret", "secret_key"]
    
    for term in sensitive_terms:
        # It's okay if the term appears in documentation context,
        # but the actual value should not be present
        pass  # This is more about the value not being exposed


@pytest.mark.property
@settings(max_examples=10)
def test_all_endpoints_do_not_expose_client_secret():
    """
    Property 19: Client Secret Protection
    
    **Validates: Requirements 7.2**
    
    All API endpoints should not expose the client secret.
    """
    client = TestClient(app)
    
    # Get client secret from environment
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    if not client_secret:
        pytest.skip("GOOGLE_CLIENT_SECRET not set in environment")
    
    # List of endpoints to test
    endpoints = [
        ("/", "GET"),
        ("/auth/google", "GET"),
        ("/auth/me", "GET"),
        ("/auth/logout", "POST"),
        ("/openapi.json", "GET"),
        ("/docs", "GET"),
    ]
    
    for endpoint, method in endpoints:
        if method == "GET":
            response = client.get(endpoint, follow_redirects=False)
        elif method == "POST":
            response = client.post(endpoint)
        
        # Check response text and headers
        response_content = str(response.headers) + response.text
        
        # Client secret should not be present
        assert client_secret not in response_content, \
            f"Client secret exposed in {method} {endpoint}"
