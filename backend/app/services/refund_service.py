"""Refund service: full/partial refunds that safely restore stock.

Refund amounts are reconciled per line item against the original line
totals, so money stays consistent even when the sale had a discount or
tax. Everything (refund rows, stock movements, transaction re-status,
audit) is a single PostgreSQL transaction.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, RefundFailedError
from app.models.enums import AuditAction, MovementType, TransactionStatus
from app.models.refund import Refund, RefundItem
from app.models.transaction import Transaction, TransactionItem
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.refund_repository import RefundRepository
from app.schemas.refund import RefundCreateIn
from app.services.audit_service import record_audit
from app.services.money import money

logger = logging.getLogger(__name__)


def _paid_factor(transaction: Transaction) -> Decimal:
    """Scale factor turning pre-tax line totals into actually-paid amounts.

    total = (subtotal - discount) * (1 + tax), so refunds must be based on
    what the customer actually paid per line, not the raw line subtotal.
    """
    if transaction.subtotal <= 0:
        return Decimal("1")
    return transaction.total / transaction.subtotal


def _proportional(item: TransactionItem, quantity: int, factor: Decimal) -> Decimal:
    """Refund cash value for a (partial) quantity of a line item."""
    if item.quantity <= 0:
        return money(Decimal("0"))
    full_line = money(item.line_total * factor)
    return money(full_line * quantity / item.quantity)


async def _load_transaction_for_update(
    session: AsyncSession, transaction_id: int
) -> Transaction | None:
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(
            selectinload(Transaction.items),
            selectinload(Transaction.refunds).selectinload(Refund.items),
        )
        .with_for_update()
    )
    return (await session.execute(stmt)).scalars().first()


async def create_refund(
    session: AsyncSession,
    data: RefundCreateIn,
    actor: User,
    ip_address: str | None = None,
) -> Refund:
    ref_repo = RefundRepository(session)
    inv_repo = InventoryRepository(session)

    transaction = await _load_transaction_for_update(session, data.transaction_id)
    if transaction is None:
        raise NotFoundError(detail=f"transaction id={data.transaction_id} not found")
    if transaction.status == TransactionStatus.REFUNDED.value:
        raise RefundFailedError(detail="transaction already fully refunded")
    if transaction.status == TransactionStatus.VOIDED.value:
        raise RefundFailedError(detail="cannot refund a voided transaction")

    item_by_id = {item.id: item for item in transaction.items}
    refunded_qty: dict[int, int] = {}
    for refund in transaction.refunds:
        for refund_item in refund.items:
            refunded_qty[refund_item.transaction_item_id] = (
                refunded_qty.get(refund_item.transaction_item_id, 0)
                + refund_item.quantity
            )

    product_ids: list[int] = []
    entries: list[tuple[TransactionItem, int, Decimal]] = []
    total_amount = Decimal("0.00")
    factor = _paid_factor(transaction)
    for req in data.items:
        item = item_by_id.get(req.transaction_item_id)
        if item is None:
            raise RefundFailedError(
                detail=f"line item id={req.transaction_item_id} not in transaction"
            )
        available = item.quantity - refunded_qty.get(req.transaction_item_id, 0)
        if req.quantity > available:
            raise RefundFailedError(
                detail=(
                    f"line item id={req.transaction_item_id}: requested "
                    f"{req.quantity}, only {available} refundable"
                )
            )
        amount = _proportional(item, req.quantity, factor)
        entries.append((item, req.quantity, amount))
        total_amount += amount
        product_ids.append(item.product_id)

    total_amount = money(total_amount)

    # Guarantee a full refund exactly matches what the customer paid.
    all_item_ids = set(item_by_id)
    requested_ids = {req.transaction_item_id for req in data.items}
    refunds_everything = (
        requested_ids == all_item_ids
        and all(
            req.quantity == item_by_id[req.transaction_item_id].quantity
            for req in data.items
        )
    )
    if refunds_everything and money(transaction.total - total_amount) > 0:
        delta = money(transaction.total - total_amount)
        adjusted_id = max(requested_ids)
        entries = [
            (item, qty, money(amount + delta) if item.id == adjusted_id else amount)
            for item, qty, amount in entries
        ]
        total_amount = money(sum((amount for _, _, amount in entries), Decimal("0.00")))
    # Lock inventory rows for every product being refunded (consistent order).
    inventory_rows = await inv_repo.get_many_for_update(sorted(set(product_ids)))
    inventory_by_product = {row.product_id: row for row in inventory_rows}
    missing = set(product_ids) - set(inventory_by_product)
    if missing:
        raise RefundFailedError(detail=f"missing inventory for products: {sorted(missing)}")

    refund = Refund(
        transaction_id=transaction.id,
        processed_by=actor.id,
        amount=total_amount,
        reason=data.reason,
    )
    refund = await ref_repo.add(refund)
    assert refund.id is not None

    for item, quantity, amount in entries:
        session.add(
            RefundItem(
                refund_id=refund.id,
                transaction_item_id=item.id,
                product_id=item.product_id,
                quantity=quantity,
                amount=amount,
            )
        )
        await inv_repo.record_movement(
            inventory_by_product[item.product_id],
            quantity_change=quantity,
            reason=MovementType.REFUND.value,
            reference_type="refund",
            reference_id=refund.id,
        )

    refunded_before = sum((r.amount for r in transaction.refunds), Decimal("0.00"))
    fully_refunded = money(refunded_before + total_amount) >= money(transaction.total)
    transaction.status = (
        TransactionStatus.REFUNDED.value
        if fully_refunded
        else TransactionStatus.PARTIALLY_REFUNDED.value
    )

    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.TRANSACTION_REFUNDED.value,
        entity_type="transaction",
        entity_id=transaction.id,
        details={
            "refund_no": refund.refund_no,
            "amount": str(total_amount),
            "transaction_no": transaction.transaction_no,
        },
        ip_address=ip_address,
    )
    await session.commit()

    logger.info(
        "refund created",
        extra={
            "refund_no": refund.refund_no,
            "transaction_no": transaction.transaction_no,
            "user_id": actor.id,
            "amount": str(total_amount),
        },
    )
    created = await ref_repo.get_detail(refund.id)
    assert created is not None
    return created
