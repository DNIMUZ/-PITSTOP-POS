"""Inventory: on-hand stock per product plus a full movement ledger."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProductInventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint(
            "stock_on_hand >= 0", name="stock_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), unique=True, index=True
    )
    stock_on_hand: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reorder_level: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product = relationship("Product", back_populates="inventory")


class StockMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "quantity_change != 0", name="quantity_change_non_zero"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    quantity_change: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(20))  # MovementType
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    product = relationship("Product")
