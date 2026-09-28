"""Inventory operations: restock, adjustments, movements ledger."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.enums import AuditAction, MovementType
from app.models.inventory import ProductInventory, StockMovement
from app.models.product import Product
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.common import Page
from app.schemas.inventory import InventoryOut, MovementOut
from app.services.audit_service import record_audit

logger = logging.getLogger(__name__)


async def adjust_stock(
    session: AsyncSession,
    product_id: int,
    quantity_change: int,
    note: str | None,
    actor: User,
) -> InventoryOut:
    """Positive change = restock, negative = adjustment. Locks the row."""
    inv_repo = InventoryRepository(session)
    pk_repo = ProductRepository(session)
    product = await pk_repo.get_by_id(product_id)
    if product is None:
        raise NotFoundError(detail=f"product id={product_id} not found")

    inventory = await inv_repo.get_for_update(product_id)
    if inventory is None:
        raise NotFoundError(detail=f"inventory for product id={product_id} missing")

    reason = (
        MovementType.RESTOCK.value
        if quantity_change > 0
        else MovementType.ADJUSTMENT.value
    )
    await inv_repo.record_movement(
        inventory,
        quantity_change=quantity_change,
        reason=reason,
        reference_type="inventory",
        note=note,
    )
    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.INVENTORY_ADJUSTED.value,
        entity_type="product",
        entity_id=product_id,
        details={"quantity_change": quantity_change, "reason": reason, "note": note},
    )
    await session.commit()
    inventory = await inv_repo.get_by_product(product_id)
    if inventory is None:
        raise NotFoundError(detail=f"inventory for product id={product_id} missing")
    return InventoryOut(
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        stock_on_hand=inventory.stock_on_hand,
        reorder_level=inventory.reorder_level,
        updated_at=inventory.updated_at,
    )


async def list_inventory(
    session: AsyncSession,
    page: int,
    page_size: int,
    low_stock_only: bool,
    q: str | None,
) -> Page[InventoryOut]:
    stmt = (
        select(ProductInventory)
        .join(Product, Product.id == ProductInventory.product_id)
        .options(selectinload(ProductInventory.product))
        .order_by(Product.name)
    )
    if low_stock_only:
        stmt = stmt.where(
            ProductInventory.stock_on_hand <= ProductInventory.reorder_level
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Product.name.ilike(like) | Product.sku.ilike(like))

    total = await session.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = (
        await session.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars()
    items = [
        InventoryOut(
            product_id=row.product_id,
            sku=row.product.sku,
            product_name=row.product.name,
            stock_on_hand=row.stock_on_hand,
            reorder_level=row.reorder_level,
            updated_at=row.updated_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, page_size=page_size, total=total)


async def list_movements(
    session: AsyncSession,
    page: int,
    page_size: int,
    product_id: int | None,
) -> Page[MovementOut]:
    stmt = (
        select(StockMovement)
        .join(Product, Product.id == StockMovement.product_id)
        .options(selectinload(StockMovement.product))
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    )
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)

    total = await session.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = (
        await session.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars()
    items = [
        MovementOut(
            id=row.id,
            product_id=row.product_id,
            sku=row.product.sku,
            product_name=row.product.name,
            quantity_change=row.quantity_change,
            reason=row.reason,
            reference_type=row.reference_type,
            reference_id=row.reference_id,
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return Page(items=items, page=page, page_size=page_size, total=total)
