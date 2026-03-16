"""Budget schemas."""

from pydantic import BaseModel, Field
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class BudgetBase(BaseModel):
    category: str = Field(..., max_length=100)
    amount: Decimal = Field(..., gt=0, description="Monthly budget limit")
    period: str = Field(default="monthly", max_length=20)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, gt=0)
    period: Optional[str] = Field(None, max_length=20)


class BudgetResponse(BudgetBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetSummaryItem(BaseModel):
    category: str
    budget_amount: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: float
    over_budget: bool


class BudgetSummaryResponse(BaseModel):
    items: List[BudgetSummaryItem]
    total_budget: Decimal
    total_spent: Decimal
