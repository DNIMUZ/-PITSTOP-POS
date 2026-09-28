"""Analytics / dashboard schemas built from real transaction aggregates."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class DailyRevenue(BaseModel):
    day: date
    revenue: Decimal
    orders: int


class TopProduct(BaseModel):
    product_id: int
    name: str
    sku: str
    quantity: int
    revenue: Decimal


class LowStockItem(BaseModel):
    product_id: int
    name: str
    sku: str
    stock_on_hand: int
    reorder_level: int


class DashboardOut(BaseModel):
    revenue_today: Decimal
    orders_today: int
    avg_order_value_today: Decimal
    items_sold_today: int
    revenue_last_7_days: list[DailyRevenue]
    top_products: list[TopProduct]
    low_stock: list[LowStockItem]
    generated_at: datetime
