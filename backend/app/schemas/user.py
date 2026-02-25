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
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "user@example.com",
                "name": "John Doe",
                "created_at": "2026-02-15T08:00:00Z"
            }
        }


class UserProfile(UserResponse):
    """Extended user profile with additional information."""
    google_id: str = Field(..., description="Google account identifier")
    
    class Config:
        from_attributes = True
