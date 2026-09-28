"""Product catalog and category operations."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.category import Category
from app.models.enums import AuditAction, MovementType
from app.models.inventory import ProductInventory
from app.models.product import Product
from app.models.user import User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.common import Page
from app.schemas.product import (
    ProductCreate,
    ProductLookupOut,
    ProductOut,
    ProductUpdate,
)
from app.services.audit_service import record_audit

logger = logging.getLogger(__name__)


async def list_categories(session: AsyncSession) -> list[Category]:
    return await ProductRepository(session).list_categories()


async def create_category(
    session: AsyncSession, name: str, description: str | None, actor: User
) -> Category:
    repo = ProductRepository(session)
    existing = await repo.get_category_by_name(name)
    if existing:
        raise ConflictError(detail=f"category '{name}' already exists")
    category = Category(name=name, description=description)
    await repo.create_category(category)
    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.CATEGORY_CREATED.value,
        entity_type="category",
        entity_id=category.id,
    )
    await session.commit()
    return category


async def list_products(
    session: AsyncSession,
    page: int,
    page_size: int,
    q: str | None,
    category_id: int | None,
    active_only: bool,
) -> Page[Product]:
    repo = ProductRepository(session)
    stmt = repo.search_stmt(q=q, category_id=category_id, active_only=active_only)
    result = await repo.paginate(stmt, page, page_size)
    return result


async def lookup_by_code(session: AsyncSession, code: str) -> ProductLookupOut:
    """Resolve a keyboard-scanner input (barcode first, then SKU)."""
    repo = ProductRepository(session)
    product = await repo.get_by_barcode(code)
    if product is None:
        product = await repo.get_by_sku(code)
    if product is None or not product.is_active:
        raise NotFoundError(detail=f"no active product for '{code}'")
    return ProductLookupOut.model_validate(product)


async def get_product(session: AsyncSession, product_id: int) -> ProductOut:
    product = await ProductRepository(session).get_by_id(product_id)
    if product is None:
        raise NotFoundError(detail=f"product id={product_id} not found")
    return ProductOut.model_validate(product)


async def create_product(session: AsyncSession, data: ProductCreate, actor: User) -> ProductOut:
    repo = ProductRepository(session)
    if await repo.get_by_sku(data.sku):
        raise ConflictError(detail=f"sku '{data.sku}' already exists")
    if data.barcode and await repo.get_by_barcode(data.barcode):
        raise ConflictError(detail=f"barcode '{data.barcode}' already exists")
    if data.category_id is not None and await repo.get_category(data.category_id) is None:
        raise NotFoundError(detail=f"category id={data.category_id} not found")

    product = Product(
        sku=data.sku,
        name=data.name,
        barcode=data.barcode,
        category_id=data.category_id,
        unit_price=data.unit_price,
        cost_price=data.cost_price,
        image_url=data.image_url,
        description=data.description,
        is_active=data.is_active,
    )
    await repo.create(product)

    inv_repo = InventoryRepository(session)
    inventory = ProductInventory(
        product_id=product.id,
        stock_on_hand=0,
        reorder_level=data.reorder_level,
    )
    session.add(inventory)
    if data.initial_stock > 0:
        await inv_repo.record_movement(
            inventory,
            quantity_change=data.initial_stock,
            reason=MovementType.INITIAL.value,
            reference_type="product",
            reference_id=product.id,
            note="initial stock",
        )

    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.PRODUCT_CREATED.value,
        entity_type="product",
        entity_id=product.id,
        details={"sku": product.sku, "name": product.name},
    )
    await session.commit()
    created = await repo.get_by_id(product.id)
    assert created is not None
    return ProductOut.model_validate(created)


async def update_product(
    session: AsyncSession, product_id: int, data: ProductUpdate, actor: User
) -> ProductOut:
    repo = ProductRepository(session)
    product = await repo.get_by_id(product_id)
    if product is None:
        raise NotFoundError(detail=f"product id={product_id} not found")

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, field, value)

    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.PRODUCT_UPDATED.value,
        entity_type="product",
        entity_id=product.id,
        details=changes,
    )
    await session.commit()
    updated = await repo.get_by_id(product.id)
    assert updated is not None
    return ProductOut.model_validate(updated)


async def deactivate_product(session: AsyncSession, product_id: int, actor: User) -> ProductOut:
    repo = ProductRepository(session)
    product = await repo.get_by_id(product_id)
    if product is None:
        raise NotFoundError(detail=f"product id={product_id} not found")
    product.is_active = False
    await record_audit(
        session,
        user_id=actor.id,
        action=AuditAction.PRODUCT_DEACTIVATED.value,
        entity_type="product",
        entity_id=product.id,
        details={"sku": product.sku},
    )
    await session.commit()
    updated = await repo.get_by_id(product.id)
    assert updated is not None
    return ProductOut.model_validate(updated)
