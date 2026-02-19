"""
Pydantic schemas for authentication.

These schemas define the data validation and serialization for authentication-related
API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TokenResponse(BaseModel):
    """Response schema for token-related endpoints."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    message: str = Field(..., description="Success message")
    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")


class OAuthCallbackResponse(BaseModel):
    """Response schema for OAuth callback."""
    success: bool = Field(..., description="Whether authentication was successful")
    message: str = Field(..., description="Status message")
    redirect_url: Optional[str] = Field(None, description="URL to redirect user to")


class LogoutResponse(BaseModel):
    """Response schema for logout."""
    message: str = Field(default="Successfully logged out", description="Logout confirmation message")


class ErrorResponse(BaseModel):
    """Response schema for authentication errors."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")
