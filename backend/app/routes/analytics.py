"""
Analytics routes for the expense tracker API.

This module provides endpoints for retrieving financial analytics including
summary statistics, monthly trends, and category breakdowns.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import structlog

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.user import User
from app.services.analytics_service import (
    get_summary,
    get_monthly_data,
    get_category_breakdown
)
from app.schemas.analytics import (
    SummaryResponse,
    MonthlyDataPoint,
    CategoryDataPoint
)


logger = structlog.get_logger()
router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryResponse)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics for the current user.
    
    Returns aggregated financial data including:
    - Total amount spent (debits)
    - Total amount received (credits)
    - Total transaction count
    - Last successful sync timestamp
    
    This endpoint provides a high-level overview of the user's financial activity.
    """
    logger.info("get_analytics_summary_request", user_id=str(current_user.id))
    
    summary = await get_summary(db=db, user_id=current_user.id)
    
    logger.info(
        "get_analytics_summary_success",
        user_id=str(current_user.id),
        total_spent=str(summary.total_spent),
        total_received=str(summary.total_received)
    )
    
    return summary


@router.get("/monthly", response_model=List[MonthlyDataPoint])
async def get_monthly_analytics(
    months: int = Query(6, ge=1, le=24, description="Number of months to retrieve"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly spending and income trends.
    
    Returns aggregated transaction data for the last N months, including:
    - Month identifier (YYYY-MM format)
    - Total amount spent in that month
    - Total amount received in that month
    - Number of transactions in that month
    
    Data is ordered by month in descending order (most recent first).
    
    - **months**: Number of months to retrieve (1-24, default: 6)
    """
    logger.info(
        "get_monthly_analytics_request",
        user_id=str(current_user.id),
        months=months
    )
    
    monthly_data = await get_monthly_data(
        db=db,
        user_id=current_user.id,
        months=months
    )
    
    logger.info(
        "get_monthly_analytics_success",
        user_id=str(current_user.id),
        data_points=len(monthly_data)
    )
    
    return monthly_data


@router.get("/categories", response_model=List[CategoryDataPoint])
async def get_category_analytics(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of categories to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get spending breakdown by merchant/category.
    
    Returns aggregated spending data grouped by merchant, including:
    - Merchant name
    - Total amount spent at that merchant
    - Number of transactions with that merchant
    - Percentage of total spending
    
    Only includes debit transactions. Data is ordered by amount in descending order
    (highest spending merchants first).
    
    - **limit**: Maximum number of categories to return (1-50, default: 10)
    """
    logger.info(
        "get_category_analytics_request",
        user_id=str(current_user.id),
        limit=limit
    )
    
    categories = await get_category_breakdown(
        db=db,
        user_id=current_user.id,
        limit=limit
    )
    
    logger.info(
        "get_category_analytics_success",
        user_id=str(current_user.id),
        categories_returned=len(categories)
    )
    
    return categories
