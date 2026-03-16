"""
Transaction model for storing financial transaction data extracted from Gmail.

This model stores transaction details parsed from bank notification emails,
with unique constraint on gmail_message_id to prevent duplicate processing.
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class TransactionTypeEnum(str, enum.Enum):
    """Enum for transaction types."""
    DEBIT = "debit"
    CREDIT = "credit"


class Transaction(Base):
    """
    Transaction model representing a financial transaction from Gmail.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        amount: Transaction amount (Numeric with 2 decimal places)
        currency: Currency code (default: INR)
        transaction_type: Type of transaction (debit or credit)
        merchant: Merchant or recipient name (optional)
        transaction_date: Date when the transaction occurred
        bank_name: Name of the bank (optional)
        gmail_message_id: Unique Gmail message ID to prevent duplicates
        category: Auto-categorized transaction category (optional)
        payment_method: Payment method used (UPI, Card, NetBanking, etc.) (optional)
        upi_reference: UPI transaction reference ID (optional)
        raw_snippet: First 500 chars of email for debugging (optional)
        created_at: Timestamp when the record was created
    """
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    merchant = Column(String(255), nullable=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    bank_name = Column(String(255), nullable=True)
    account_label = Column(String(128), nullable=True, index=True)  # e.g. "HDFC Savings", "ICICI Credit Card"
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)

    # New fields for enhanced functionality
    category = Column(String(100), nullable=True, index=True)
    payment_method = Column(String(50), nullable=True)
    upi_reference = Column(String(255), nullable=True, index=True)
    raw_snippet = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, type={self.transaction_type}, "
            f"merchant={self.merchant}, category={self.category})>"
        )
