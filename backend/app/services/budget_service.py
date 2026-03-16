"""Budget service for CRUD and spend-vs-budget calculations."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract

from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetSummaryItem


async def get_budgets(db: AsyncSession, user_id: UUID) -> List[Budget]:
    """Get all budgets for a user."""
    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id).order_by(Budget.category)
    )
    return list(result.scalars().all())


async def create_budget(
    db: AsyncSession, user_id: UUID, category: str, amount: Decimal, period: str = "monthly"
) -> Budget:
    """Create a budget. Replaces existing budget for same category."""
    existing = await db.execute(
        select(Budget).where(
            and_(Budget.user_id == user_id, Budget.category == category)
        )
    )
    old = existing.scalar_one_or_none()
    if old:
        old.amount = amount
        old.period = period
        await db.commit()
        await db.refresh(old)
        return old

    budget = Budget(user_id=user_id, category=category, amount=amount, period=period)
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def update_budget(
    db: AsyncSession, budget_id: UUID, user_id: UUID, amount: Optional[Decimal] = None
) -> Optional[Budget]:
    """Update a budget."""
    result = await db.execute(
        select(Budget).where(
            and_(Budget.id == budget_id, Budget.user_id == user_id)
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        return None
    if amount is not None:
        budget.amount = amount
    await db.commit()
    await db.refresh(budget)
    return budget


async def delete_budget(db: AsyncSession, budget_id: UUID, user_id: UUID) -> bool:
    """Delete a budget."""
    result = await db.execute(
        select(Budget).where(
            and_(Budget.id == budget_id, Budget.user_id == user_id)
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        return False
    await db.delete(budget)
    await db.commit()
    return True


async def get_budget_summary(
    db: AsyncSession, user_id: UUID
) -> tuple[List[BudgetSummaryItem], Decimal, Decimal]:
    """
    Get spend vs budget for current month per category.
    Returns (items, total_budget, total_spent).
    """
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    budgets = await get_budgets(db, user_id)
    if not budgets:
        return [], Decimal(0), Decimal(0)

    items: List[BudgetSummaryItem] = []
    total_budget = Decimal(0)
    total_spent = Decimal(0)

    for b in budgets:
        spent_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "debit",
                Transaction.transaction_date >= start_of_month,
                Transaction.category == b.category
            )
        )
        r = await db.execute(spent_query)
        spent = Decimal(str(r.scalar()))
        remaining = b.amount - spent
        percent_used = (float(spent) / float(b.amount) * 100) if b.amount else 0

        items.append(BudgetSummaryItem(
            category=b.category,
            budget_amount=b.amount,
            spent=spent,
            remaining=remaining,
            percent_used=round(percent_used, 1),
            over_budget=spent > b.amount
        ))
        total_budget += b.amount
        total_spent += spent

    return items, total_budget, total_spent
