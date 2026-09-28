"""Refund schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RefundItemIn(BaseModel):
    transaction_item_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class RefundCreateIn(BaseModel):
    transaction_id: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)
    items: list[RefundItemIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _dedupe_items(self) -> RefundCreateIn:
        seen: set[int] = set()
        for item in self.items:
            if item.transaction_item_id in seen:
                raise ValueError("duplicate transaction_item_id in items")
            seen.add(item.transaction_item_id)
        return self


class RefundItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_item_id: int
    product_id: int
    quantity: int
    amount: Decimal


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    refund_no: str
    transaction_id: int
    processed_by: int
    amount: Decimal
    reason: str | None = None
    created_at: datetime
    items: list[RefundItemOut]
