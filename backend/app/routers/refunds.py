"""Refunds: process refunds against a transaction (manager+)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.deps import CurrentUser, DbDep, RequireManager
from app.models.user import User
from app.repositories.refund_repository import RefundRepository
from app.schemas.refund import RefundCreateIn, RefundOut
from app.services.refund_service import create_refund

router = APIRouter(prefix="/api/v1/transactions", tags=["refunds"])


@router.post(
    "/{transaction_id}/refund",
    response_model=RefundOut,
    status_code=201,
    summary="Refund a transaction (full or partial)",
    dependencies=[Depends(RequireManager)],
)
async def process_refund(
    transaction_id: int,
    body: RefundCreateIn,
    request: Request,
    db: DbDep,
    actor: User = Depends(RequireManager),
) -> RefundOut:
    if body.transaction_id != transaction_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="transaction_id in body does not match path")
    refund = await create_refund(db, body, actor, ip_address=_client_ip(request))
    return RefundOut.model_validate(refund)


@router.get(
    "/{transaction_id}/refunds",
    response_model=list[RefundOut],
    summary="List refunds for a transaction",
)
async def refunds_for_transaction(
    transaction_id: int,
    db: DbDep,
    user: CurrentUser,
) -> list[RefundOut]:
    from app.core.errors import ForbiddenError, NotFoundError
    from app.models.enums import UserRole
    from app.repositories.transaction_repository import TransactionRepository

    tx = await TransactionRepository(db).get_detail(transaction_id)
    if tx is None:
        raise NotFoundError(detail=f"transaction id={transaction_id} not found")
    manager_view = user.role in (UserRole.ADMIN.value, UserRole.MANAGER.value)
    if not manager_view and tx.cashier_id != user.id:
        raise ForbiddenError("cashiers can only view their own transactions")
    refunds = await RefundRepository(db).list_for_transaction(transaction_id)
    return [RefundOut.model_validate(r) for r in refunds]


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
