"""
Authentication routes for OAuth and session management.

This module provides endpoints for Google OAuth login, callback handling,
user profile retrieval, and logout.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.database import get_db
from app.models.user import User
from app.auth.oauth import initiate_oauth_flow, handle_oauth_callback
from app.auth.jwt_handler import create_session_token, verify_session_token
from jose import JWTError
from app.auth.encryption import encrypt_refresh_token
from app.auth.middleware import get_current_user
from app.schemas.user import UserResponse
from app.schemas.auth import LogoutResponse
import os
import structlog

logger = structlog.get_logger()


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/set-session")
async def set_session_cookie(
    token: str,
    response: Response
):
    """
    Set session cookie from token.
    
    This endpoint is called by the frontend after OAuth redirect to set the
    HTTPOnly cookie. This works around the issue of cookies not persisting
    across domain redirects.
    
    Validates the JWT token before setting to prevent session hijacking.
    
    Args:
        token: JWT session token.
        response: FastAPI response object for setting cookies.
        
    Returns:
        Success message.
    """
    try:
        verify_session_token(token)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    return {"success": True, "message": "Session cookie set"}


@router.get("/google")
async def google_auth():
    """
    Initiate Google OAuth flow.
    
    Redirects the user to Google's OAuth consent screen to authorize
    the application to access their Gmail and profile information.
    
    Returns:
        RedirectResponse: Redirect to Google OAuth authorization URL.
    """
    try:
        # Generate OAuth authorization URL
        auth_url = initiate_oauth_flow()
        
        # Redirect user to Google OAuth consent screen
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate OAuth flow: {str(e)}"
        )


@router.get("/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback with CSRF protection.
    
    Validates the state parameter, exchanges the authorization code for tokens,
    creates or updates the user in the database, encrypts the refresh token,
    generates a session JWT, and redirects to frontend with token.
    
    Handles OAuth error redirects (user denied, etc.) by redirecting to login.
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    logger.info("auth_callback_entry", has_code=bool(code), has_state=bool(state), error=error, error_description=error_description)
    
    # OAuth error case: user denied or Google returned an error
    if error:
        _msg = error_description or error
        _redirect = f"{frontend_url}/login?error={_msg.replace(' ', '+')}" if _msg else f"{frontend_url}/login"
        return RedirectResponse(url=_redirect)
    
    if not code or not state:
        logger.warning("auth_callback_missing_params", has_code=bool(code), has_state=bool(state))
        return RedirectResponse(url=f"{frontend_url}/login?error=Missing+code+or+state")
    
    try:
        # Validate CSRF state parameter
        from app.auth.oauth import validate_and_consume_state
        logger.info("auth_callback_step", step="validate_state")
        if not validate_and_consume_state(state):
            logger.warning("auth_callback_invalid_state")
            return RedirectResponse(url=f"{frontend_url}/login?error=Invalid+or+expired+session")
        logger.info("auth_callback_step", step="state_valid")
        
        # Exchange authorization code for tokens (includes gmail.readonly scope, token exchange, user info from ID token)
        logger.info("auth_callback_step", step="token_exchange_start")
        oauth_result = handle_oauth_callback(code)
        logger.info("auth_callback_step", step="token_exchange_ok", has_access_token=bool(oauth_result.get("access_token")), has_refresh_token=bool(oauth_result.get("refresh_token")), has_email=bool(oauth_result.get("email")), has_google_id=bool(oauth_result.get("google_id")))
        
        email = oauth_result.get("email")
        name = oauth_result.get("name")
        google_id = oauth_result.get("google_id")
        logger.info("auth_callback_step", step="user_info_extract", email=email, name=name, google_id=google_id)
        if not google_id:
            logger.error("auth_callback_user_info_failure", reason="missing_google_id")
            raise ValueError("Google did not return user ID")
        if not email:
            logger.error("auth_callback_user_info_failure", reason="missing_email")
            raise ValueError("Google did not return email")
        
        refresh_token = oauth_result["refresh_token"]
        name = name or email.split("@")[0]  # Fallback if name missing
        
        # Encrypt refresh token before storing
        logger.info("auth_callback_step", step="encrypt_token")
        encrypted_refresh_token = encrypt_refresh_token(refresh_token)
        
        # Check if user already exists (requires users table - run: alembic upgrade head)
        logger.info("auth_callback_step", step="db_lookup")
        try:
            result = await db.execute(
                select(User).where(User.google_id == google_id)
            )
            user = result.scalar_one_or_none()
        except Exception as db_err:
            err_str = str(db_err).lower()
            if "does not exist" in err_str or "relation" in err_str or "table" in err_str:
                logger.error("auth_callback_db_error", error=str(db_err), hint="Database table missing - run: alembic upgrade head")
            else:
                logger.error("auth_callback_db_error", error=str(db_err), error_type=type(db_err).__name__)
            raise
        logger.info("auth_callback_step", step="db_lookup_ok", user_exists=user is not None)
        
        if user:
            # Update existing user's refresh token
            user.refresh_token_encrypted = encrypted_refresh_token
            user.name = name  # Update name in case it changed
            user.email = email  # Update email in case it changed
        else:
            # Create new user
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                google_id=google_id,
                refresh_token_encrypted=encrypted_refresh_token
            )
            db.add(user)
        
        logger.info("auth_callback_step", step="db_commit")
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as db_err:
            err_str = str(db_err).lower()
            if "does not exist" in err_str or "relation" in err_str or "table" in err_str:
                logger.error("auth_callback_db_commit_error", error=str(db_err), hint="Database table missing - run: alembic upgrade head")
            else:
                logger.error("auth_callback_db_commit_error", error=str(db_err), error_type=type(db_err).__name__)
            raise
        logger.info("auth_callback_step", step="db_commit_ok", user_id=str(user.id))
        
        # Generate JWT session token
        logger.info("auth_callback_step", step="jwt_create")
        session_token = create_session_token(str(user.id), user.email)

        # Redirect to frontend auth-complete with token in URL.
        # Cookie cannot persist across cross-origin redirect (backend -> frontend),
        # so frontend calls /auth/set-session to set the cookie.
        redirect_response = RedirectResponse(
            url=f"{frontend_url}/auth/complete?token={session_token}"
        )

        return redirect_response
        
    except HTTPException:
        raise  # Re-raise HTTPExceptions (e.g. 400) as-is, don't convert to 500
    except ValueError as e:
        logger.error("auth_callback_value_error", error=str(e), error_type="ValueError")
        return RedirectResponse(url=f"{frontend_url}/login?error=OAuth+failed")
    except Exception as e:
        logger.error("auth_callback_exception", error=str(e), error_type=type(e).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires valid JWT session token in cookie.
    
    Args:
        current_user: Current authenticated user from middleware.
        
    Returns:
        UserResponse: Current user's profile information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response):
    """
    Logout the current user.
    
    Clears the session cookie to invalidate the user's session.
    
    Args:
        response: FastAPI response object for clearing cookies.
        
    Returns:
        LogoutResponse: Logout confirmation message.
    """
    # Clear the session cookie (path must match how it was set)
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "development") == "production",
        samesite="lax"
    )
    
    return LogoutResponse(message="Successfully logged out")
