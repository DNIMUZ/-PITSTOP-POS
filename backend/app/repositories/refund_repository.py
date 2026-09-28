"""Refund repository."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.refund import Refund
from app.repositories.base import BaseRepository


class RefundRepository(BaseRepository):
    async def add(self, refund: Refund) -> Refund:
        self.session.add(refund)
        await self.session.flush()
        return refund

    async def get_detail(self, refund_id: int) -> Refund | None:
        return await self.session.scalar(
            select(Refund)
            .where(Refund.id == refund_id)
            .options(selectinload(Refund.items))
        )

    async def list_for_transaction(self, transaction_id: int) -> list[Refund]:
        return list(
            (
                await self.session.execute(
                    select(Refund)
                    .where(Refund.transaction_id == transaction_id)
                    .order_by(Refund.created_at)
                    .options(selectinload(Refund.items))
                )
            ).scalars()
        )
