"""Transaction / checkout schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PaymentMethod
from app.schemas.refund import RefundOut


class TransactionItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=9999)


class PaymentIn(BaseModel):
    method: PaymentMethod
    amount: Decimal | None = Field(default=None, ge=Decimal("0.0"))
    reference: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _require_reference_for_card_or_qr(self) -> PaymentIn:
        if self.method in (PaymentMethod.CARD, PaymentMethod.QR) and not self.reference:
            raise ValueError(
                f"reference is required for {self.method.value} payments"
            )
        return self


class TransactionCreateIn(BaseModel):
    items: list[TransactionItemIn] = Field(min_length=1)
    discount_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    payment: PaymentIn

    @model_validator(mode="after")
    def _dedupe_items(self) -> TransactionCreateIn:
        seen: set[int] = set()
        for item in self.items:
            if item.product_id in seen:
                raise ValueError("duplicate product_id in items")
            seen.add(item.product_id)
        return self


class TransactionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    method: str
    amount: Decimal
    status: str
    transaction_reference: str | None = None
    created_at: datetime


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_no: str
    cashier_id: int
    cashier_name: str | None = None
    items_count: int
    subtotal: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    tendered_amount: Decimal | None = None
    change_amount: Decimal | None = None
    status: str
    created_at: datetime


class TransactionDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_no: str
    cashier_id: int
    cashier_name: str | None = None
    subtotal: Decimal
    discount_rate: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    tendered_amount: Decimal | None = None
    change_amount: Decimal | None = None
    status: str
    created_at: datetime
    items: list[TransactionItemOut]
    payments: list[PaymentOut]
    refunds: list[RefundOut]
