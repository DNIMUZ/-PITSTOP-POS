"""Analytics / dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import DbDep, RequireManager
from app.models.user import User
from app.schemas.analytics import DashboardOut
from app.services.analytics_service import get_dashboard

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="Live dashboard metrics from real transaction data",
    dependencies=[Depends(RequireManager)],
)
async def dashboard(db: DbDep, _actor: User = Depends(RequireManager)) -> DashboardOut:
    return await get_dashboard(db)
