"""
Google OAuth 2.0 flow implementation.

This module handles the OAuth authentication flow with Google, including
authorization URL generation, token exchange, and token refresh.
"""

import os
import secrets
import time
from threading import Lock
from typing import Dict
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException


# OAuth 2.0 scopes required for the application
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# In-memory CSRF state store: {state: expiration_timestamp}
_oauth_state_store: Dict[str, float] = {}
_state_store_lock = Lock()
STATE_TTL_SECONDS = 600  # 10 minutes


def get_oauth_config() -> Dict[str, str]:
    """
    Get OAuth configuration from environment variables.
    
    Returns:
        dict: Configuration with client_id, client_secret, and redirect_uri.
        
    Raises:
        ValueError: If required OAuth environment variables are not set.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is not set")
    if not client_secret:
        raise ValueError("GOOGLE_CLIENT_SECRET environment variable is not set")
    if not redirect_uri:
        raise ValueError("GOOGLE_REDIRECT_URI environment variable is not set")
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }


def initiate_oauth_flow() -> str:
    """
    Generate the OAuth authorization URL for Google login with CSRF protection.
    
    Returns:
        str: The authorization URL to redirect the user to.
        
    Raises:
        ValueError: If OAuth configuration is invalid.
    """
    config = get_oauth_config()
    
    # Create OAuth flow configuration
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config["redirect_uri"]]
        }
    }
    
    # Create the flow
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=config["redirect_uri"]
    )
    
    # Generate cryptographically secure state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state with expiration timestamp
    with _state_store_lock:
        _oauth_state_store[state] = time.time() + STATE_TTL_SECONDS
    
    # Generate authorization URL with state parameter
    authorization_url, _ = flow.authorization_url(
        access_type='offline',  # Request refresh token
        include_granted_scopes='true',
        prompt='consent',  # Force consent screen to get refresh token
        state=state  # Add CSRF state parameter
    )
    
    return authorization_url


def validate_and_consume_state(state: str) -> bool:
    """
    Validate OAuth state parameter and remove from store (consume).
    
    This function checks if the state exists, hasn't expired, and removes it
    to prevent replay attacks.
    
    Args:
        state: The state parameter to validate.
        
    Returns:
        bool: True if state is valid, False otherwise.
    """
    if not state:
        return False
    
    with _state_store_lock:
        # Check if state exists
        if state not in _oauth_state_store:
            return False
        
        # Check if expired
        if time.time() > _oauth_state_store[state]:
            del _oauth_state_store[state]
            return False
        
        # Valid state - consume it (remove from store to prevent replay)
        del _oauth_state_store[state]
        return True


def cleanup_expired_states():
    """
    Remove expired states from store.
    
    This function should be called periodically to prevent memory leaks
    from expired but unconsumed states.
    """
    with _state_store_lock:
        current_time = time.time()
        expired = [s for s, exp in _oauth_state_store.items() if current_time > exp]
        for state in expired:
            del _oauth_state_store[state]


def handle_oauth_callback(code: str) -> Dict[str, str]:
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        code: The authorization code received from Google OAuth callback.
        
    Returns:
        dict: Dictionary containing access_token, refresh_token, and user info.
        
    Raises:
        ValueError: If code is empty or token exchange fails.
    """
    if not code:
        raise ValueError("Authorization code cannot be empty")
    
    config = get_oauth_config()
    
    # Create OAuth flow configuration
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config["redirect_uri"]]
        }
    }
    
    # Create the flow
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=config["redirect_uri"]
    )
    
    try:
        # Exchange code for tokens
        flow.fetch_token(code=code)
        
        # Get credentials
        credentials = flow.credentials
        
        if not credentials.refresh_token:
            raise ValueError("No refresh token received. User may need to revoke access and re-authenticate.")
        
        # Get user info from ID token
        import google.auth.transport.requests
        import google.oauth2.id_token
        
        request = google.auth.transport.requests.Request()
        # Add clock skew tolerance of 10 seconds
        id_info = google.oauth2.id_token.verify_oauth2_token(
            credentials.id_token,
            request,
            config["client_id"],
            clock_skew_in_seconds=10
        )
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "email": id_info.get("email"),
            "name": id_info.get("name"),
            "google_id": id_info.get("sub")
        }
        
    except Exception as e:
        raise ValueError(f"Token exchange failed: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RequestException)
)
def refresh_access_token(refresh_token: str) -> str:
    """
    Obtain a new access token using a refresh token.
    
    This function includes retry logic with exponential backoff for handling
    transient network errors.
    
    Args:
        refresh_token: The refresh token to use for obtaining a new access token.
        
    Returns:
        str: The new access token.
        
    Raises:
        ValueError: If refresh_token is empty or token refresh fails.
        RequestException: If network request fails after retries.
    """
    if not refresh_token:
        raise ValueError("Refresh token cannot be empty")
    
    config = get_oauth_config()
    
    try:
        # Create credentials with the refresh token
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config["client_id"],
            client_secret=config["client_secret"]
        )
        
        # Refresh the token
        request = Request()
        credentials.refresh(request)
        
        if not credentials.token:
            raise ValueError("Failed to obtain new access token")
        
        return credentials.token
        
    except Exception as e:
        raise ValueError(f"Token refresh failed: {str(e)}")


async def refresh_access_token_async(refresh_token: str) -> str:
    """
    Async wrapper for token refresh to avoid blocking the event loop.
    
    Wraps the synchronous refresh_access_token function with run_in_executor
    to prevent blocking the FastAPI event loop during token refresh operations.
    
    Args:
        refresh_token: The refresh token to use for obtaining a new access token.
        
    Returns:
        str: The new access token.
        
    Raises:
        ValueError: If refresh_token is empty or token refresh fails.
        RequestException: If network request fails after retries.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=5)
    
    return await loop.run_in_executor(executor, refresh_access_token, refresh_token)
