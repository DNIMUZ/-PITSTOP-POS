"""Sales transactions: checkout, listing, detail."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbDep
from app.core.errors import ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.common import Page
from app.schemas.transaction import (
    TransactionCreateIn,
    TransactionDetailOut,
    TransactionOut,
)
from app.services.transaction_service import create_transaction

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@router.post(
    "",
    response_model=TransactionDetailOut,
    status_code=201,
    summary="Complete a sale (atomic checkout)",
)
async def checkout(
    body: TransactionCreateIn,
    db: DbDep,
    user: CurrentUser,
) -> TransactionDetailOut:
    transaction = await create_transaction(db, body, user)
    detail = await TransactionRepository(db).get_detail(transaction.id)
    assert detail is not None
    return TransactionDetailOut.model_validate(detail)


@router.get("", response_model=Page[TransactionOut], summary="List transactions")
async def list_transactions(
    db: DbDep,
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=50),
    status: str | None = Query(default=None, max_length=30),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> Page[TransactionOut]:
    repo = TransactionRepository(db)
    manager_view = user.role in (UserRole.ADMIN.value, UserRole.MANAGER.value)
    cashier_filter = None if manager_view else user.id
    if not manager_view and cashier_filter is None:
        raise ForbiddenError("cashiers can only view their own transactions")

    stmt = await repo.list_stmt(
        cashier_id=cashier_filter,
        status=status,
        q=q,
        date_from=_iso(date_from),
        date_to=_iso(date_to),
    )
    result = await repo.paginate(stmt, page, page_size)
    items = [TransactionOut.model_validate(t) for t in result.items]
    return Page(
        items=items,
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/{transaction_id}", response_model=TransactionDetailOut, summary="Transaction detail")
async def get_transaction(
    transaction_id: int, db: DbDep, user: CurrentUser
) -> TransactionDetailOut:
    repo = TransactionRepository(db)
    transaction = await repo.get_detail(transaction_id)
    if transaction is None:
        raise NotFoundError(detail=f"transaction id={transaction_id} not found")
    manager_view = user.role in (UserRole.ADMIN.value, UserRole.MANAGER.value)
    if not manager_view and transaction.cashier_id != user.id:
        raise ForbiddenError("cashiers can only view their own transactions")
    return TransactionDetailOut.model_validate(transaction)
