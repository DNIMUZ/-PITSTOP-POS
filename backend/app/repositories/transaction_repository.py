"""Transaction repository: reads + persistence for sales."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.refund import Refund
from app.models.transaction import Transaction, TransactionItem
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository):
    async def get_by_no(self, transaction_no: str) -> Transaction | None:
        return await self.session.scalar(
            select(Transaction).where(Transaction.transaction_no == transaction_no)
        )

    async def get_detail(self, transaction_id: int) -> Transaction | None:
        return await self.session.scalar(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                selectinload(Transaction.cashier),
                selectinload(Transaction.items).selectinload(TransactionItem.product),
                selectinload(Transaction.payments),
                selectinload(Transaction.refunds).selectinload(Refund.items),
            )
        )

    async def add(self, transaction: Transaction) -> Transaction:
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def list_stmt(
        self,
        cashier_id: int | None = None,
        status: str | None = None,
        q: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ):
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.cashier),
                selectinload(Transaction.items),
            )
            .order_by(Transaction.created_at.desc())
        )
        if cashier_id is not None:
            stmt = stmt.where(Transaction.cashier_id == cashier_id)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if q:
            stmt = stmt.where(Transaction.transaction_no.ilike(f"%{q}%"))
        if date_from:
            stmt = stmt.where(Transaction.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.created_at <= date_to)
        return stmt

    async def count_created_today(self) -> int:
        start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return (
            await self.session.scalar(
                select(func.count()).select_from(Transaction).where(
                    Transaction.created_at >= start
                )
            )
            or 0
        )
