"""Product schemas. Money fields serialize as strings (never floats)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: int | None = Field(default=None, gt=0)
    unit_price: Decimal = Field(ge=Decimal("0.0"), max_digits=12, decimal_places=2)
    cost_price: Decimal | None = Field(
        default=None, ge=Decimal("0.0"), max_digits=12, decimal_places=2
    )
    image_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    is_active: bool = True
    initial_stock: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=5, ge=0)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: int | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(
        default=None, ge=Decimal("0.0"), max_digits=12, decimal_places=2
    )
    cost_price: Decimal | None = Field(
        default=None, ge=Decimal("0.0"), max_digits=12, decimal_places=2
    )
    image_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    barcode: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    unit_price: Decimal
    cost_price: Decimal | None = None
    image_url: str | None = None
    description: str | None = None
    is_active: bool
    stock_on_hand: int
    reorder_level: int
    created_at: datetime


class ProductLookupOut(BaseModel):
    """Minimal payload returned when a barcode / SKU scan resolves a product."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    barcode: str | None = None
    unit_price: Decimal
    stock_on_hand: int
    image_url: str | None = None
    category_name: str | None = None
