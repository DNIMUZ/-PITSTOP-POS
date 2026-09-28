"""Base repository with an agnostic pagination helper."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import Page


class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def paginate(self, stmt: Any, page: int, page_size: int) -> Page[Any]:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.session.scalar(count_stmt) or 0
        results = (
            await self.session.execute(
                stmt.offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars()
        return Page(
            items=list(results.all()),
            page=page,
            page_size=page_size,
            total=total,
        )
