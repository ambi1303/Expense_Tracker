"""
Pydantic schemas for Transaction model.

These schemas define the data validation and serialization for transaction-related
API requests and responses.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    DEBIT = "debit"
    CREDIT = "credit"


class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(default="INR", max_length=10, description="Currency code")
    transaction_type: TransactionType = Field(..., description="Transaction type (debit or credit)")
    merchant: Optional[str] = Field(None, max_length=255, description="Merchant name")
    transaction_date: datetime = Field(..., description="Transaction date and time")
    bank_name: Optional[str] = Field(None, max_length=255, description="Bank name")
    account_label: Optional[str] = Field(None, max_length=128, description="Account/card label e.g. HDFC Credit Card")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Validate that amount is positive and has at most 2 decimal places."""
        if v <= 0:
            raise ValueError('Amount must be positive')
        # Check decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError('Amount can have at most 2 decimal places')
        return v
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        """Validate currency code."""
        if not v or len(v) < 3:
            raise ValueError('Currency code must be at least 3 characters')
        return v.upper()


class TransactionResponse(TransactionBase):
    """Transaction response schema for API responses."""
    id: UUID = Field(..., description="Unique transaction identifier")
    user_id: UUID = Field(..., description="User identifier")
    gmail_message_id: str = Field(..., description="Gmail message ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "amount": "1250.50",
                "currency": "INR",
                "transaction_type": "debit",
                "merchant": "Amazon India",
                "transaction_date": "2026-02-19T10:30:00Z",
                "bank_name": "HDFC Bank",
                "gmail_message_id": "18d4f2a3b5c6d7e8",
                "created_at": "2026-02-19T10:35:00Z"
            }
        }


class TransactionListResponse(BaseModel):
    """Response schema for paginated transaction list."""
    transactions: List[TransactionResponse] = Field(..., description="List of transactions")
    total: int = Field(..., ge=0, description="Total number of transactions")
    page: int = Field(..., ge=0, description="Current page number (0-indexed)")
    limit: int = Field(..., ge=1, le=100, description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more pages")
    
    class Config:
        from_attributes = True


class TransactionFilterParams(BaseModel):
    """Query parameters for filtering transactions."""
    transaction_type: Optional[TransactionType] = Field(None, description="Filter by transaction type")
    start_date: Optional[str] = Field(None, description="Filter transactions after this date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter transactions before this date (YYYY-MM-DD)")
    merchant: Optional[str] = Field(None, max_length=255, description="Filter by merchant name (partial match)")
    bank_name: Optional[str] = Field(None, max_length=255, description="Filter by bank name")
    account_label: Optional[str] = Field(None, max_length=128, description="Filter by account/card label")
    min_amount: Optional[Decimal] = Field(None, gt=0, description="Minimum transaction amount")
    max_amount: Optional[Decimal] = Field(None, gt=0, description="Maximum transaction amount")
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate and parse date string."""
        if v:
            try:
                # Try to parse as date
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @field_validator('max_amount')
    @classmethod
    def validate_amount_range(cls, v, info):
        """Validate that max_amount is greater than min_amount."""
        if v and info.data.get('min_amount') and v < info.data['min_amount']:
            raise ValueError('max_amount must be greater than min_amount')
        return v


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    gmail_message_id: str = Field(..., max_length=255, description="Gmail message ID")
    
    @field_validator('gmail_message_id')
    @classmethod
    def validate_message_id(cls, v):
        """Validate that message ID is not empty."""
        if not v or not v.strip():
            raise ValueError('Gmail message ID cannot be empty')
        return v.strip()
