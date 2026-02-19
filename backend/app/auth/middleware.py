"""
Authentication middleware for FastAPI.

This module provides dependency functions for validating JWT tokens and
retrieving the current authenticated user.
"""

from fastapi import Cookie, HTTPException, status, Depends
from typing import Optional
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import verify_session_token
from app.database import get_db
from app.models.user import User
from sqlalchemy import select


async def get_current_user(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency function to get the current authenticated user from JWT cookie.
    
    This function validates the JWT token from the session_token cookie and
    retrieves the corresponding user from the database.
    
    Args:
        session_token: JWT token from HTTPOnly cookie.
        db: Database session dependency.
        
    Returns:
        User: The authenticated user object.
        
    Raises:
        HTTPException: 401 Unauthorized if token is missing, invalid, or user not found.
    """
    # Check if token is present
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Session token missing.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Verify and decode the token
        payload = verify_session_token(session_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Retrieve user from database
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


async def get_optional_current_user(
    session_token: Optional[str] = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency function to optionally get the current authenticated user.
    
    Similar to get_current_user but returns None instead of raising an exception
    if the user is not authenticated. Useful for endpoints that work differently
    for authenticated vs unauthenticated users.
    
    Args:
        session_token: JWT token from HTTPOnly cookie.
        db: Database session dependency.
        
    Returns:
        User | None: The authenticated user object or None if not authenticated.
    """
    if not session_token:
        return None
    
    try:
        # Verify and decode the token
        payload = verify_session_token(session_token)
        user_id = payload.get("user_id")
        
        if not user_id:
            return None
        
        # Retrieve user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        return user
        
    except (JWTError, ValueError, Exception):
        # Return None for any authentication errors
        return None
