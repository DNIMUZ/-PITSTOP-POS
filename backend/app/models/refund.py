"""Refunds (full and partial), restoring stock through the movement ledger."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="refund_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    refund_no: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
        server_default=sa_text("'RFD-' || lpad(nextval('refund_no_seq')::text, 8, '0')"),
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="RESTRICT"), index=True
    )
    processed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    transaction = relationship("Transaction", back_populates="refunds")
    items = relationship(
        "RefundItem", back_populates="refund", cascade="all, delete-orphan"
    )


class RefundItem(Base):
    __tablename__ = "refund_items"
    __table_args__ = (
        CheckConstraint(
            "quantity > 0", name="refund_quantity_positive"
        ),
        CheckConstraint(
            "amount >= 0", name="refund_item_amount_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    refund_id: Mapped[int] = mapped_column(
        ForeignKey("refunds.id", ondelete="CASCADE"), index=True
    )
    transaction_item_id: Mapped[int] = mapped_column(
        ForeignKey("transaction_items.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # refunded line amount

    refund = relationship("Refund", back_populates="items")
    transaction_item = relationship("TransactionItem")
