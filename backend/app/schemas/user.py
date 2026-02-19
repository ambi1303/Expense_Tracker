"""
Pydantic schemas for User model.

These schemas define the data validation and serialization for user-related
API requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")


class UserResponse(UserBase):
    """User response schema for API responses."""
    id: UUID = Field(..., description="Unique user identifier")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class UserProfile(UserResponse):
    """Extended user profile with additional information."""
    google_id: str = Field(..., description="Google account identifier")
    
    class Config:
        from_attributes = True
