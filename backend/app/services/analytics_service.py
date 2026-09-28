"""Dashboard analytics computed from real transaction/inventory data."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import ProductInventory
from app.models.product import Product
from app.models.refund import Refund
from app.models.transaction import Transaction, TransactionItem
from app.schemas.analytics import (
    DailyRevenue,
    DashboardOut,
    LowStockItem,
    TopProduct,
)
from app.services.money import money

logger = logging.getLogger(__name__)


async def get_dashboard(session: AsyncSession) -> DashboardOut:
    now = datetime.now(UTC)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_30d = now - timedelta(days=30)

    sales_row = (
        await session.execute(
            select(
                func.coalesce(func.sum(Transaction.total), Decimal("0")),
                func.count(Transaction.id),
            ).where(
                Transaction.created_at >= start_today,
                Transaction.status != "voided",
            )
        )
    ).one()
    sales_today: Decimal = Decimal(sales_row[0])
    orders_today = int(sales_row[1])

    items_row = (
        await session.execute(
            select(func.coalesce(func.sum(TransactionItem.quantity), 0)).select_from(
                TransactionItem
            ).join(Transaction, TransactionItem.transaction_id == Transaction.id).where(
                Transaction.created_at >= start_today,
                Transaction.status != "voided",
            )
        )
    ).scalar_one()
    items_sold_today = int(items_row)

    refunds_today = Decimal(
        (
            await session.execute(
                select(func.coalesce(func.sum(Refund.amount), Decimal("0"))).select_from(
                    Refund
                ).join(Transaction, Refund.transaction_id == Transaction.id).where(
                    Transaction.created_at >= start_today
                )
            )
        ).scalar_one()
    )
    revenue_today = money(sales_today - refunds_today)
    avg_order = money(revenue_today / orders_today) if orders_today else Decimal("0.00")

    daily = await _daily_revenue(session, start_7d)
    top = await _top_products(session, start_30d)
    low_stock = await _low_stock(session)

    return DashboardOut(
        revenue_today=revenue_today,
        orders_today=orders_today,
        avg_order_value_today=avg_order,
        items_sold_today=items_sold_today,
        revenue_last_7_days=daily,
        top_products=top,
        low_stock=low_stock,
        generated_at=now,
    )


async def _daily_revenue(session: AsyncSession, since: datetime) -> list[DailyRevenue]:
    day = func.date_trunc("day", Transaction.created_at)
    sales = (
        await session.execute(
            select(
                day.label("day"),
                func.coalesce(func.sum(Transaction.total), Decimal("0")),
                func.count(Transaction.id),
            )
            .where(Transaction.created_at >= since, Transaction.status != "voided")
            .group_by("day")
        )
    ).all()
    refunds = (
        await session.execute(
            select(
                func.date_trunc("day", Transaction.created_at).label("day"),
                func.coalesce(func.sum(Refund.amount), Decimal("0")),
            )
            .select_from(Refund)
            .join(Transaction, Refund.transaction_id == Transaction.id)
            .where(Transaction.created_at >= since)
            .group_by("day")
        )
    ).all()
    refund_map = {row[0]: Decimal(row[1]) for row in refunds}

    result: list[DailyRevenue] = []
    for row in sales:
        day_value: datetime = row[0]
        revenue = money(Decimal(row[1]) - refund_map.get(day_value, Decimal("0")))
        result.append(
            DailyRevenue(day=day_value.date(), revenue=revenue, orders=int(row[2]))
        )
    return result


async def _top_products(session: AsyncSession, since: datetime) -> list[TopProduct]:
    rows = (
        await session.execute(
            select(
                TransactionItem.product_id,
                Product.name,
                Product.sku,
                func.sum(TransactionItem.quantity),
                func.sum(TransactionItem.line_total),
            )
            .join(Transaction, TransactionItem.transaction_id == Transaction.id)
            .join(Product, TransactionItem.product_id == Product.id)
            .where(Transaction.created_at >= since, Transaction.status != "voided")
            .group_by(
                TransactionItem.product_id,
                Product.name,
                Product.sku,
            )
            .order_by(func.sum(TransactionItem.quantity).desc())
            .limit(10)
        )
    ).all()
    return [
        TopProduct(
            product_id=r[0],
            name=r[1],
            sku=r[2],
            quantity=int(r[3]),
            revenue=Decimal(r[4]),
        )
        for r in rows
    ]


async def _low_stock(session: AsyncSession) -> list[LowStockItem]:
    rows = (
        await session.execute(
            select(
                ProductInventory.product_id,
                Product.name,
                Product.sku,
                ProductInventory.stock_on_hand,
                ProductInventory.reorder_level,
            )
            .join(Product, ProductInventory.product_id == Product.id)
            .where(ProductInventory.stock_on_hand <= ProductInventory.reorder_level)
            .order_by(ProductInventory.stock_on_hand)
        )
    ).all()
    return [
        LowStockItem(
            product_id=r[0],
            name=r[1],
            sku=r[2],
            stock_on_hand=int(r[3]),
            reorder_level=int(r[4]),
        )
        for r in rows
    ]
