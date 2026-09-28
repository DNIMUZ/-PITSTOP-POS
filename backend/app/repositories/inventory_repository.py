"""Inventory repository: on-hand stock + movement ledger.

Stock races are resolved by locking the `inventory` row itself
(SELECT ... FOR UPDATE) so a second cashier always sees the committed
stock level before validating their sale.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.inventory import ProductInventory, StockMovement
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    async def get_by_product(self, product_id: int) -> ProductInventory | None:
        return await self.session.scalar(
            select(ProductInventory).where(ProductInventory.product_id == product_id)
        )

    async def get_for_update(self, product_id: int) -> ProductInventory | None:
        return await self.session.scalar(
            select(ProductInventory)
            .where(ProductInventory.product_id == product_id)
            .with_for_update()
        )

    async def get_many_for_update(self, product_ids: list[int]) -> list[ProductInventory]:
        """Lock inventory rows in a consistent order to avoid deadlocks."""
        stmt = (
            select(ProductInventory)
            .where(ProductInventory.product_id.in_(product_ids))
            .order_by(ProductInventory.product_id)
            .with_for_update()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def record_movement(
        self,
        inventory: ProductInventory,
        quantity_change: int,
        reason: str,
        reference_type: str | None = None,
        reference_id: int | None = None,
        note: str | None = None,
    ) -> None:
        """Adjust stock and append a ledger entry inside the calling DB transaction."""
        new_stock = inventory.stock_on_hand + quantity_change
        if new_stock < 0:
            from app.core.errors import InsufficientStockError

            raise InsufficientStockError(
                detail=(
                    f"product_id={inventory.product_id} "
                    f"change={quantity_change} available={inventory.stock_on_hand}"
                )
            )
        inventory.stock_on_hand = new_stock
        self.session.add(
            StockMovement(
                product_id=inventory.product_id,
                quantity_change=quantity_change,
                reason=reason,
                reference_type=reference_type,
                reference_id=reference_id,
                note=note,
            )
        )

    async def movements_for_product(self, product_id: int) -> list[StockMovement]:
        return list(
            (
                await self.session.execute(
                    select(StockMovement)
                    .where(StockMovement.product_id == product_id)
                    .order_by(StockMovement.created_at.desc())
                )
            ).scalars()
        )

    async def list_movements_stmt(self, product_id: int | None = None, limit: int = 200):
        stmt = (
            select(StockMovement)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
        )
        if product_id is not None:
            stmt = stmt.where(StockMovement.product_id == product_id)
        return stmt
