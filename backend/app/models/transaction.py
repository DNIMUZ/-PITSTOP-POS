"""Sales transactions, line items and payments."""
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
    func,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Transaction(Base):
    @property
    def cashier_name(self) -> str | None:
        return self.cashier.full_name if self.cashier else None

    @property
    def items_count(self) -> int:
        return len(self.items) if self.items else 0

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint(
            "discount_amount <= subtotal", name="discount_not_exceeding_subtotal"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_no: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
        server_default=sa_text("'TXN-' || lpad(nextval('txn_no_seq')::text, 8, '0')"),
    )
    cashier_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0"), server_default="0"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0"
    )
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), server_default="0"
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tendered_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    change_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="completed", server_default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    cashier = relationship("User", back_populates="transactions")
    items = relationship(
        "TransactionItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="TransactionItem.id",
    )
    payments = relationship(
        "Payment", back_populates="transaction", cascade="all, delete-orphan"
    )
    refunds = relationship(
        "Refund", back_populates="transaction", cascade="all, delete-orphan"
    )


class TransactionItem(Base):
    @property
    def sku(self) -> str:
        return self.product.sku if self.product else ""

    __tablename__ = "transaction_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("line_total >= 0", name="line_total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(160))  # snapshot at sale time
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(20))  # PaymentMethod
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(30), default="recorded")  # PaymentStatus
    transaction_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    transaction = relationship("Transaction", back_populates="payments")
