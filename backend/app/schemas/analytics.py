"""
Pydantic schemas for Analytics endpoints.

These schemas define the data validation and serialization for analytics-related
API responses including summary statistics, monthly data, and category breakdowns.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


class SummaryResponse(BaseModel):
    """
    Summary statistics response schema.
    
    Provides high-level overview of user's financial transactions including
    total amounts spent and received, transaction count, and last sync time.
    """
    total_spent: Decimal = Field(..., ge=0, description="Total amount spent (debits)")
    total_received: Decimal = Field(..., ge=0, description="Total amount received (credits)")
    transaction_count: int = Field(..., ge=0, description="Total number of transactions")
    last_sync: Optional[datetime] = Field(None, description="Timestamp of last successful sync")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "total_spent": "15420.50",
                "total_received": "25000.00",
                "transaction_count": 47,
                "last_sync": "2024-02-18T10:30:00Z"
            }
        }


class MonthlyDataPoint(BaseModel):
    """
    Monthly spending data point schema.
    
    Represents aggregated transaction data for a specific month,
    including both spending (debits) and income (credits).
    """
    month: str = Field(..., description="Month in YYYY-MM format")
    spent: Decimal = Field(..., ge=0, description="Total amount spent in this month")
    received: Decimal = Field(..., ge=0, description="Total amount received in this month")
    transaction_count: int = Field(..., ge=0, description="Number of transactions in this month")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "month": "2024-02",
                "spent": "3250.75",
                "received": "5000.00",
                "transaction_count": 12
            }
        }


class CategoryDataPoint(BaseModel):
    """
    Category/merchant spending breakdown schema.
    
    Represents spending aggregated by merchant or category,
    including the total amount and percentage of overall spending.
    """
    merchant: str = Field(..., description="Merchant or category name")
    amount: Decimal = Field(..., ge=0, description="Total amount spent at this merchant")
    transaction_count: int = Field(..., ge=0, description="Number of transactions with this merchant")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total spending")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "merchant": "Amazon",
                "amount": "2450.00",
                "transaction_count": 8,
                "percentage": 15.89
            }
        }


class SpendingByCategoryPoint(BaseModel):
    """Spending aggregated by inferred category."""
    category: str = Field(..., description="Category name")
    amount: Decimal = Field(..., ge=0, description="Total spent in this category")
    transaction_count: int = Field(..., ge=0, description="Number of transactions")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total spending")


class CategoryMonthlyPoint(BaseModel):
    """Monthly spending per category for trends."""
    month: str = Field(..., description="YYYY-MM")
    category: str = Field(..., description="Category name")
    amount: Decimal = Field(..., ge=0, description="Spent in this category this month")


class InsightItem(BaseModel):
    """Single insight for the user."""
    type: str = Field(..., description="insight type: trend, top_category, comparison, suggestion")
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Descriptive message")
    value: Optional[str] = Field(None, description="Optional numeric/value")
