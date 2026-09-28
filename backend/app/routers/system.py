"""Health and version endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.deps import DbDep

router = APIRouter(tags=["system"])


class HealthOut(BaseModel):
    status: str


class HealthDbOut(BaseModel):
    status: str
    database: str


class VersionOut(BaseModel):
    name: str
    version: str
    environment: str


@router.get("/health", response_model=HealthOut, summary="Liveness probe")
async def health() -> HealthOut:
    return HealthOut(status="healthy")


@router.get("/health/db", response_model=HealthDbOut, summary="Database connectivity probe")
async def health_db(db: DbDep, response: Response) -> HealthDbOut:
    try:
        await db.execute(text("SELECT 1"))
        return HealthDbOut(status="healthy", database="ok")
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthDbOut(status="unhealthy", database="unreachable")


@router.get(
    "/api/v1/version",
    response_model=VersionOut,
    summary="Application version",
)
async def version() -> VersionOut:
    settings = get_settings()
    return VersionOut(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
