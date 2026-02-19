"""
SyncLog model for tracking email synchronization operations.

This model stores logs of sync operations, including success/failure status
and the number of emails processed for each user.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SyncLog(Base):
    """
    SyncLog model representing a synchronization operation log.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        status: Status of the sync operation (success, partial, failed)
        emails_processed: Number of emails successfully processed
        errors: Error messages if sync failed (optional)
        created_at: Timestamp when the sync operation occurred
    """
    __tablename__ = "sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(String(50), nullable=False)
    emails_processed = Column(Integer, default=0, nullable=False)
    errors = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self) -> str:
        return (
            f"<SyncLog(id={self.id}, user_id={self.user_id}, "
            f"status={self.status}, emails_processed={self.emails_processed})>"
        )
