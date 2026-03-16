"""
Analytics service for calculating financial statistics.

This module provides functions for generating summary statistics, monthly trends,
and category breakdowns from transaction data.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, case
import structlog

from app.models.transaction import Transaction
from app.models.sync_log import SyncLog
from app.schemas.analytics import (
    SummaryResponse, MonthlyDataPoint, CategoryDataPoint,
    SpendingByCategoryPoint, CategoryMonthlyPoint, InsightItem,
)


logger = structlog.get_logger()


async def get_summary(
    db: AsyncSession,
    user_id: UUID
) -> SummaryResponse:
    """
    Get summary statistics for a user's transactions.
    
    Calculates total spent (debits), total received (credits), transaction count,
    and last sync time.
    
    Args:
        db: Database session.
        user_id: User ID to get summary for.
        
    Returns:
        SummaryResponse with aggregated statistics.
    """
    logger.info("get_summary_started", user_id=str(user_id))
    
    # Calculate total spent (debits)
    spent_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit"
        )
    )
    spent_result = await db.execute(spent_query)
    total_spent = spent_result.scalar()
    
    # Calculate total received (credits)
    received_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "credit"
        )
    )
    received_result = await db.execute(received_query)
    total_received = received_result.scalar()
    
    # Get transaction count
    count_query = select(func.count(Transaction.id)).where(
        Transaction.user_id == user_id
    )
    count_result = await db.execute(count_query)
    transaction_count = count_result.scalar()
    
    # Get last sync time
    last_sync_query = select(SyncLog.created_at).where(
        and_(
            SyncLog.user_id == user_id,
            SyncLog.status == "success"
        )
    ).order_by(SyncLog.created_at.desc()).limit(1)
    last_sync_result = await db.execute(last_sync_query)
    last_sync = last_sync_result.scalar_one_or_none()
    
    logger.info(
        "get_summary_success",
        user_id=str(user_id),
        total_spent=str(total_spent),
        total_received=str(total_received),
        transaction_count=transaction_count
    )
    
    return SummaryResponse(
        total_spent=Decimal(str(total_spent)),
        total_received=Decimal(str(total_received)),
        transaction_count=transaction_count,
        last_sync=last_sync
    )


async def get_monthly_data(
    db: AsyncSession,
    user_id: UUID,
    months: int = 6
) -> List[MonthlyDataPoint]:
    """
    Get monthly spending and income data for the last N months.
    
    Aggregates transactions by month, calculating total spent, received,
    and transaction count for each month.
    
    Args:
        db: Database session.
        user_id: User ID to get data for.
        months: Number of months to retrieve (default: 6).
        
    Returns:
        List of MonthlyDataPoint objects, ordered by month descending.
    """
    logger.info("get_monthly_data_started", user_id=str(user_id), months=months)
    
    # Calculate start date (N months ago) using proper month arithmetic
    start_date = datetime.now(timezone.utc) - relativedelta(months=months)
    
    # Query for monthly aggregation
    # Group by year and month
    query = select(
        extract('year', Transaction.transaction_date).label('year'),
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(
            case(
                (Transaction.transaction_type == "debit", Transaction.amount),
                else_=0
            )
        ).label('spent'),
        func.sum(
            case(
                (Transaction.transaction_type == "credit", Transaction.amount),
                else_=0
            )
        ).label('received'),
        func.count(Transaction.id).label('transaction_count')
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date
        )
    ).group_by(
        extract('year', Transaction.transaction_date),
        extract('month', Transaction.transaction_date)
    ).order_by(
        extract('year', Transaction.transaction_date).desc(),
        extract('month', Transaction.transaction_date).desc()
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to MonthlyDataPoint objects
    monthly_data = []
    for row in rows:
        year = int(row.year)
        month = int(row.month)
        month_str = f"{year}-{month:02d}"
        
        monthly_data.append(MonthlyDataPoint(
            month=month_str,
            spent=Decimal(str(row.spent or 0)),
            received=Decimal(str(row.received or 0)),
            transaction_count=row.transaction_count
        ))
    
    logger.info(
        "get_monthly_data_success",
        user_id=str(user_id),
        months_returned=len(monthly_data)
    )
    
    return monthly_data


async def get_category_breakdown(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10
) -> List[CategoryDataPoint]:
    """
    Get spending breakdown by merchant/category with normalized merchant names.
    
    Aggregates debit transactions by merchant using case-insensitive grouping,
    calculating total amount, transaction count, and percentage of total spending.
    Merchant names are normalized (lowercase for grouping, capitalized for display).
    
    Args:
        db: Database session.
        user_id: User ID to get breakdown for.
        limit: Maximum number of categories to return (default: 10).
        
    Returns:
        List of CategoryDataPoint objects, ordered by amount descending.
    """
    logger.info("get_category_breakdown_started", user_id=str(user_id), limit=limit)
    
    # First, get total spending for percentage calculation
    total_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit"
        )
    )
    total_result = await db.execute(total_query)
    total_spent = float(total_result.scalar())
    
    # Query for category breakdown with case-insensitive merchant grouping
    query = select(
        func.lower(Transaction.merchant).label('merchant_lower'),
        func.sum(Transaction.amount).label('amount'),
        func.count(Transaction.id).label('transaction_count')
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.merchant.isnot(None)
        )
    ).group_by(
        func.lower(Transaction.merchant)
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to CategoryDataPoint objects with capitalized merchant names
    categories = []
    for row in rows:
        amount = float(row.amount)
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        
        # Capitalize merchant name for display
        merchant_display = row.merchant_lower.capitalize()
        
        categories.append(CategoryDataPoint(
            merchant=merchant_display,
            amount=Decimal(str(amount)),
            transaction_count=row.transaction_count,
            percentage=round(percentage, 2)
        ))
    
    logger.info(
        "get_category_breakdown_success",
        user_id=str(user_id),
        categories_returned=len(categories)
    )
    
    return categories


async def get_spending_by_category(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 15,
    months: int = 6,
) -> List[SpendingByCategoryPoint]:
    """
    Get spending breakdown by inferred category.
    Uses category when set, otherwise groups uncategorized as "Uncategorized".
    """
    start_date = datetime.now(timezone.utc) - relativedelta(months=months)
    total_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= start_date,
        )
    )
    total_r = await db.execute(total_q)
    total = float(total_r.scalar())
    
    cat_coalesce = func.coalesce(Transaction.category, "Uncategorized")
    cat_q = select(
        cat_coalesce.label("category"),
        func.sum(Transaction.amount).label("amount"),
        func.count(Transaction.id).label("count"),
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= start_date,
        )
    ).group_by(cat_coalesce).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(limit)
    r = await db.execute(cat_q)
    rows = r.all()
    
    return [
        SpendingByCategoryPoint(
            category=row.category,
            amount=Decimal(str(row.amount)),
            transaction_count=row.count,
            percentage=round((float(row.amount) / total * 100), 2) if total > 0 else 0,
        )
        for row in rows
    ]


async def get_category_monthly_trends(
    db: AsyncSession,
    user_id: UUID,
    months: int = 6,
    top_categories: int = 5,
) -> List[CategoryMonthlyPoint]:
    """Get monthly spending per category for charting trends."""
    start_date = datetime.now(timezone.utc) - relativedelta(months=months)
    cat_coalesce = func.coalesce(Transaction.category, "Uncategorized")
    q = select(
        extract("year", Transaction.transaction_date).label("year"),
        extract("month", Transaction.transaction_date).label("month"),
        cat_coalesce.label("category"),
        func.sum(Transaction.amount).label("amount"),
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= start_date,
        )
    ).group_by(
        extract("year", Transaction.transaction_date),
        extract("month", Transaction.transaction_date),
        cat_coalesce,
    ).order_by(
        extract("year", Transaction.transaction_date).desc(),
        extract("month", Transaction.transaction_date).desc(),
        func.sum(Transaction.amount).desc(),
    )
    r = await db.execute(q)
    return [
        CategoryMonthlyPoint(
            month=f"{int(row.year)}-{int(row.month):02d}",
            category=row.category,
            amount=Decimal(str(row.amount)),
        )
        for row in r.all()
    ]


async def get_insights(
    db: AsyncSession,
    user_id: UUID,
) -> List[InsightItem]:
    """Generate intelligent insights from transaction data."""
    now = datetime.now(timezone.utc)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = this_month_start - relativedelta(months=1)
    two_months_ago = this_month_start - relativedelta(months=2)
    
    insights: List[InsightItem] = []
    
    # This month spent
    q_this = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= this_month_start,
        )
    )
    # Last month spent
    q_last = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= last_month_start,
            Transaction.transaction_date < this_month_start,
        )
    )
    r_this = await db.execute(q_this)
    r_last = await db.execute(q_last)
    this_spent = float(r_this.scalar())
    last_spent = float(r_last.scalar())
    
    if last_spent > 0 and this_spent > 0:
        pct_change = ((this_spent - last_spent) / last_spent) * 100
        if abs(pct_change) >= 5:
            direction = "more" if pct_change > 0 else "less"
            insights.append(InsightItem(
                type="comparison",
                title="Month-over-month",
                message=f"You spent {abs(pct_change):.0f}% {direction} this month compared to last month.",
                value=f"{pct_change:+.0f}%",
            ))
    
    # Top category this month (reuse coalesce expr so GROUP BY matches SELECT)
    cat_coalesce = func.coalesce(Transaction.category, "Uncategorized")
    cat_q = select(
        cat_coalesce.label("category"),
        func.sum(Transaction.amount).label("amount"),
    ).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            Transaction.transaction_date >= this_month_start,
        )
    ).group_by(cat_coalesce).order_by(
        func.sum(Transaction.amount).desc()
    ).limit(1)
    cr = await db.execute(cat_q)
    top_row = cr.fetchone()
    if top_row and top_row.amount and this_spent > 0:
        pct = (float(top_row.amount) / this_spent) * 100
        insights.append(InsightItem(
            type="top_category",
            title="Top category this month",
            message=f"'{top_row.category}' accounts for {pct:.0f}% of your spending.",
            value=top_row.category,
        ))
    
    # Uncategorized count
    uncat_q = select(func.count(Transaction.id)).where(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",
            or_(Transaction.category.is_(None), Transaction.category == ""),
            Transaction.transaction_date >= two_months_ago,
        )
    )
    ur = await db.execute(uncat_q)
    uncat = ur.scalar()
    if uncat and uncat > 0:
        insights.append(InsightItem(
            type="suggestion",
            title="Improve categorization",
            message=f"You have {uncat} uncategorized transactions. Use 'Auto-categorize' to assign categories automatically.",
            value=str(uncat),
        ))
    
    return insights
