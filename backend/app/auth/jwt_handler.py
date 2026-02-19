"""
JWT token handling for session management.

This module provides functions for creating and verifying JWT session tokens
used for user authentication after OAuth login.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from jose import JWTError, jwt


def get_jwt_config() -> Dict[str, any]:
    """
    Get JWT configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary with secret, algorithm, and expiration.
        
    Raises:
        ValueError: If required JWT environment variables are not set.
    """
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable is not set")
    
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expiration_days = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))
    
    return {
        "secret": secret,
        "algorithm": algorithm,
        "expiration_days": expiration_days
    }


def create_session_token(user_id: str, email: str) -> str:
    """
    Create a JWT session token for an authenticated user.
    
    Args:
        user_id: The unique identifier of the user.
        email: The user's email address.
        
    Returns:
        str: The encoded JWT token.
        
    Raises:
        ValueError: If user_id or email is empty.
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")
    if not email:
        raise ValueError("email cannot be empty")
    
    config = get_jwt_config()
    
    # Calculate expiration time
    expiration = datetime.now(timezone.utc) + timedelta(days=config["expiration_days"])
    
    # Create token payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "email": email,
        "exp": expiration,  # Expiration time
        "iat": datetime.now(timezone.utc)  # Issued at time
    }
    
    # Encode and return the token
    token = jwt.encode(payload, config["secret"], algorithm=config["algorithm"])
    return token


def verify_session_token(token: str) -> Dict[str, any]:
    """
    Verify and decode a JWT session token.
    
    Args:
        token: The JWT token to verify.
        
    Returns:
        dict: The decoded token payload containing user_id and email.
        
    Raises:
        ValueError: If token is empty.
        JWTError: If token is invalid, expired, or verification fails.
    """
    if not token:
        raise ValueError("token cannot be empty")
    
    config = get_jwt_config()
    
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            config["secret"],
            algorithms=[config["algorithm"]]
        )
        
        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise JWTError("Token payload missing required fields")
        
        return {
            "user_id": user_id,
            "email": email
        }
        
    except JWTError as e:
        # Re-raise JWT errors for the caller to handle
        raise JWTError(f"Token verification failed: {str(e)}")
