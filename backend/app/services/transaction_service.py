"""Transactional sale service.

The whole sale — transaction, items, payment, inventory deduction and
audit log — runs inside one PostgreSQL transaction. If any step fails
the entire operation is rolled back and nothing is persisted.

Concurrency: product and inventory rows are locked with
SELECT ... FOR UPDATE (acquired in a consistent order). A second
cashier selling the same last unit blocks on the lock, re-reads the
committed stock and safely fails with INSUFFICIENT_STOCK.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, TransactionFailedError
from app.models.enums import AuditAction, MovementType, PaymentStatus
from app.models.product import Product
from app.models.transaction import Payment, Transaction, TransactionItem
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreateIn
from app.services.audit_service import record_audit
from app.services.money import money

logger = logging.getLogger(__name__)

_PAYMENT_REF_PREFIX = {
    "cash": "CASH",
    "card": "CARD",
    "qr": "QR",
    "ewallet": "EW",
}


async def create_transaction(
    session: AsyncSession,
    data: TransactionCreateIn,
    cashier: User,
    ip_address: str | None = None,
) -> Transaction:
    settings = get_settings()
    product_repo = ProductRepository(session)
    inv_repo = InventoryRepository(session)
    tx_repo = TransactionRepository(session)

    product_ids = sorted({item.product_id for item in data.items})
    try:
        products = await product_repo.get_many_for_update(product_ids)
        inventory_rows = await inv_repo.get_many_for_update(product_ids)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("transaction lock failure", extra={"error": str(exc), "ids": product_ids})
        raise TransactionFailedError(detail="could not acquire stock locks") from exc

    product_by_id = {p.id: p for p in products}
    if len(product_by_id) != len(product_ids):
        missing = set(product_ids) - set(product_by_id)
        raise NotFoundError(detail=f"unknown products: {sorted(missing)}")
    for p in products:
        if not p.is_active:
            raise ConflictError(detail=f"product {p.sku} is inactive")

    inventory_by_product = {row.product_id: row for row in inventory_rows}
    missing_inventory = set(product_ids) - set(inventory_by_product)
    if missing_inventory:
        raise ConflictError(
            detail=f"no inventory record for products: {sorted(missing_inventory)}"
        )

    item_rows: list[tuple[Product, int]] = []
    subtotal = Decimal("0.00")
    for item in data.items:
        product = product_by_id[item.product_id]
        available = inventory_by_product[item.product_id].stock_on_hand
        if item.quantity > available:
            raise TransactionFailedError(
                detail=(
                    f"{product.sku}: requested {item.quantity}, "
                    f"only {available} in stock"
                )
            )
        line_total = money(product.unit_price * item.quantity)
        subtotal += line_total
        item_rows.append((product, item.quantity))

    discount_amount, tax_amount, total = _totals(
        subtotal, data.discount_rate, settings.tax_rate_decimal
    )

    tendered = data.payment.amount if data.payment.amount is not None else total
    if tendered < total:
        raise TransactionFailedError(
            detail=f"tendered {tendered} is less than total due {total}"
        )
    change = money(tendered - total) if _is_cash(data.payment.method.value) else None

    transaction = Transaction(
        cashier_id=cashier.id,
        subtotal=money(subtotal),
        discount_rate=money(data.discount_rate),
        discount_amount=discount_amount,
        tax_rate=settings.tax_rate_decimal,
        tax_amount=tax_amount,
        total=total,
        tendered_amount=tendered if _is_cash(data.payment.method.value) else data.payment.amount,
        change_amount=change,
        status="completed",
    )
    transaction = await tx_repo.add(transaction)
    assert transaction.id is not None

    for product, quantity in item_rows:
        line_total = money(product.unit_price * quantity)
        session.add(
            TransactionItem(
                transaction_id=transaction.id,
                product_id=product.id,
                product=product,
                product_name=product.name,
                unit_price=product.unit_price,
                quantity=quantity,
                line_total=line_total,
            )
        )
        await inv_repo.record_movement(
            inventory_by_product[product.id],
            quantity_change=-quantity,
            reason=MovementType.SALE.value,
            reference_type="transaction",
            reference_id=transaction.id,
        )

    ref = data.payment.reference or _generate_reference(
        data.payment.method.value, transaction.id
    )
    session.add(
        Payment(
            transaction_id=transaction.id,
            method=data.payment.method.value,
            amount=tendered,
            status=PaymentStatus.RECORDED.value,
            transaction_reference=ref,
        )
    )

    await record_audit(
        session,
        user_id=cashier.id,
        action=AuditAction.TRANSACTION_CREATED.value,
        entity_type="transaction",
        entity_id=transaction.id,
        details={"transaction_no": transaction.transaction_no, "total": str(total)},
        ip_address=ip_address,
    )
    await session.commit()

    logger.info(
        "transaction created",
        extra={
            "transaction_no": transaction.transaction_no,
            "user_id": cashier.id,
            "total": str(transaction.total),
            "items": len(item_rows),
        },
    )
    return transaction


def _totals(
    subtotal: Decimal, discount_rate: Decimal, tax_rate: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    from app.services.money import compute_totals

    return compute_totals(subtotal, discount_rate, tax_rate)


def _is_cash(method: str) -> bool:
    return method == "cash"


def _generate_reference(method: str, id_: int) -> str:
    prefix = _PAYMENT_REF_PREFIX.get(method, "PAY")
    # Recorded locally only; not a gateway-approved reference.
    return f"{prefix}-{id_:06d}"
