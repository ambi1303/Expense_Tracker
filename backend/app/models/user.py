"""
User model for storing authenticated user information.

This model stores user data from Google OAuth authentication, including
encrypted refresh tokens for Gmail API access.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User model representing an authenticated user.
    
    Attributes:
        id: Unique identifier (UUID)
        email: User's email address (unique)
        name: User's display name
        google_id: Google account identifier (unique)
        refresh_token_encrypted: Encrypted OAuth refresh token for Gmail access
        created_at: Timestamp when the user was created
        updated_at: Timestamp when the user was last updated
        transactions: Relationship to Transaction model
        sync_logs: Relationship to SyncLog model
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token_encrypted = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"
