"""Budget model for monthly spending limits per category."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Budget(Base):
    """
    Budget model for monthly spending limits per category.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        category: Category name (e.g. Food, Shopping, Transport)
        amount: Monthly budget limit
        period: Budget period (monthly)
        created_at: Timestamp when the record was created
    """
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    category = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    period = Column(String(20), default="monthly", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Budget(id={self.id}, category={self.category}, amount={self.amount})>"
