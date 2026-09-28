"""Products: CRUD, server-side search, pagination and barcode lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbDep, RequireCashier, RequireManager
from app.models.user import User
from app.schemas.common import Page
from app.schemas.product import (
    ProductCreate,
    ProductLookupOut,
    ProductOut,
    ProductUpdate,
)
from app.services import product_service

router = APIRouter(
    prefix="/api/v1/products",
    tags=["products"],
    dependencies=[Depends(RequireCashier)],
)


@router.get("", response_model=Page[ProductOut], summary="List/search products")
async def list_products(
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, ge=1),
    active_only: bool = Query(default=True),
) -> Page[ProductOut]:
    result = await product_service.list_products(
        db, page, page_size, q, category_id, active_only
    )
    return Page(
        items=[ProductOut.model_validate(p) for p in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get(
    "/lookup/{code}",
    response_model=ProductLookupOut,
    summary="Resolve a barcode/SKU scan to a product",
)
async def lookup_product(code: str, db: DbDep) -> ProductLookupOut:
    return await product_service.lookup_by_code(db, code)


@router.get("/{product_id}", response_model=ProductOut, summary="Get product by id")
async def get_product(product_id: int, db: DbDep) -> ProductOut:
    return await product_service.get_product(db, product_id)


@router.post(
    "",
    response_model=ProductOut,
    status_code=201,
    summary="Create product",
    dependencies=[Depends(RequireManager)],
)
async def create_product(
    body: ProductCreate, db: DbDep, actor: User = Depends(RequireManager)
) -> ProductOut:
    return await product_service.create_product(db, body, actor)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="Update product",
    dependencies=[Depends(RequireManager)],
)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: DbDep,
    actor: User = Depends(RequireManager),
) -> ProductOut:
    return await product_service.update_product(db, product_id, body, actor)


@router.delete(
    "/{product_id}",
    response_model=ProductOut,
    summary="Deactivate product (soft delete)",
    dependencies=[Depends(RequireManager)],
)
async def deactivate_product(
    product_id: int, db: DbDep, actor: User = Depends(RequireManager)
) -> ProductOut:
    return await product_service.deactivate_product(db, product_id, actor)
