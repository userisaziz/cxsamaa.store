"""Analytics aggregation endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_operator_up
from src.database import get_db
from src.models.user import User
from src.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsSalespeopleResponse,
)
from src.services.analytics import (
    get_analytics_overview,
    get_salespeople_comparison,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(
    brand_id: str | None = Query(None),
    store_id: str | None = Query(None),
    salesperson_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    return await get_analytics_overview(
        db, brand_id=brand_id, store_id=store_id,
        salesperson_id=salesperson_id,
        date_from=date_from, date_to=date_to,
    )


@router.get("/salespeople-comparison", response_model=AnalyticsSalespeopleResponse)
async def analytics_salespeople_comparison(
    brand_id: str | None = Query(None),
    store_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_operator_up),
):
    return await get_salespeople_comparison(
        db, brand_id=brand_id, store_id=store_id,
        date_from=date_from, date_to=date_to,
    )
