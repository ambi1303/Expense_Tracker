"""Budget routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.user import User
from app.services.budget_service import (
    get_budgets,
    create_budget,
    update_budget,
    delete_budget,
    get_budget_summary,
)
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetSummaryResponse, BudgetSummaryItem


router = APIRouter(prefix="/budgets", tags=["budgets"])

DEFAULT_CATEGORIES = [
    "Food", "Groceries", "Shopping", "Transport", "Bills",
    "Entertainment", "Healthcare", "Education", "Other"
]


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all budgets for the current user."""
    budgets = await get_budgets(db, current_user.id)
    return budgets


@router.get("/categories")
async def get_available_categories(
    current_user: User = Depends(get_current_user),
):
    """Get list of suggested categories for budgets."""
    return {"categories": DEFAULT_CATEGORIES}


@router.get("/summary", response_model=BudgetSummaryResponse)
async def budget_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get spend vs budget for current month per category."""
    items, total_budget, total_spent = await get_budget_summary(db, current_user.id)
    return BudgetSummaryResponse(
        items=items,
        total_budget=total_budget,
        total_spent=total_spent,
    )


@router.post("", response_model=BudgetResponse)
async def create_budget_route(
    data: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or replace a budget for a category."""
    budget = await create_budget(
        db, current_user.id, data.category, data.amount, data.period
    )
    return budget


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget_route(
    budget_id: str,
    data: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a budget."""
    from uuid import UUID
    try:
        bid = UUID(budget_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid budget ID")
    budget = await update_budget(db, bid, current_user.id, amount=data.amount)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.delete("/{budget_id}")
async def delete_budget_route(
    budget_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a budget."""
    from uuid import UUID
    try:
        bid = UUID(budget_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid budget ID")
    ok = await delete_budget(db, bid, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"success": True}
