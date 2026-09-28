"""Inventory schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    sku: str
    product_name: str
    stock_on_hand: int
    reorder_level: int
    updated_at: datetime


class StockAdjustIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity_change: int = Field(ne=0)
    note: str | None = Field(default=None, max_length=255)


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    sku: str
    product_name: str
    quantity_change: int
    reason: str
    reference_type: str | None = None
    reference_id: int | None = None
    note: str | None = None
    created_at: datetime
