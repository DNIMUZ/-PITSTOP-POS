"""Product repository with server-side search."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.repositories.base import BaseRepository

_PRODUCT_LOADS = (
    selectinload(Product.inventory),
    selectinload(Product.category),
)


class ProductRepository(BaseRepository):
    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.session.scalar(
            select(Product).where(Product.id == product_id).options(*_PRODUCT_LOADS)
        )

    async def get_by_sku(self, sku: str) -> Product | None:
        return await self.session.scalar(
            select(Product).where(Product.sku == sku).options(*_PRODUCT_LOADS)
        )

    async def get_by_barcode(self, barcode: str) -> Product | None:
        return await self.session.scalar(
            select(Product).where(Product.barcode == barcode).options(*_PRODUCT_LOADS)
        )

    async def get_many_for_update(self, ids: list[int]) -> list[Product]:
        """Lock the product rows (SELECT ... FOR UPDATE) during a transactional sale."""
        stmt = (
            select(Product)
            .where(Product.id.in_(ids))
            .order_by(Product.id)
            .with_for_update()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product

    def search_stmt(
        self,
        q: str | None = None,
        category_id: int | None = None,
        active_only: bool = True,
    ):
        stmt = select(Product).options(*_PRODUCT_LOADS).order_by(Product.name)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Product.barcode.ilike(like),
                )
            )
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        return stmt

    async def list_categories(self) -> list[Category]:
        return list(
            (
                await self.session.execute(
                    select(Category).order_by(Category.name)
                )
            ).scalars()
        )

    async def get_category(self, category_id: int) -> Category | None:
        return await self.session.scalar(
            select(Category).where(Category.id == category_id)
        )

    async def get_category_by_name(self, name: str) -> Category | None:
        return await self.session.scalar(
            select(Category).where(Category.name == name)
        )

    async def create_category(self, category: Category) -> Category:
        self.session.add(category)
        await self.session.flush()
        return category
