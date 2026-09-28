"""Inventory: stock levels, restock/adjust, movements ledger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbDep, RequireCashier, RequireManager
from app.models.user import User
from app.schemas.common import Page
from app.schemas.inventory import InventoryOut, MovementOut, StockAdjustIn
from app.services import inventory_service

router = APIRouter(
    prefix="/api/v1/inventory",
    tags=["inventory"],
    dependencies=[Depends(RequireCashier)],
)


@router.get("", response_model=Page[InventoryOut], summary="List stock levels")
async def list_inventory(
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
    low_stock_only: bool = Query(default=False),
) -> Page[InventoryOut]:
    return await inventory_service.list_inventory(
        db, page, page_size, low_stock_only, q
    )


@router.get(
    "/movements",
    response_model=Page[MovementOut],
    summary="List inventory movements (ledger)",
    dependencies=[Depends(RequireManager)],
)
async def list_movements(
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    product_id: int | None = Query(default=None, ge=1),
) -> Page[MovementOut]:
    return await inventory_service.list_movements(db, page, page_size, product_id)


@router.post(
    "/adjust",
    response_model=InventoryOut,
    summary="Restock (+) or adjust (-) stock",
    dependencies=[Depends(RequireManager)],
)
async def adjust_stock(
    body: StockAdjustIn, db: DbDep, actor: User = Depends(RequireManager)
) -> InventoryOut:
    return await inventory_service.adjust_stock(
        db, body.product_id, body.quantity_change, body.note, actor
    )
