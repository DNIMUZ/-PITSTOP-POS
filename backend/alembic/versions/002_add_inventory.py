"""002_add_inventory: inventory + inventory_movements ledger.

Revision ID: 002_add_inventory
Revises: 001_initial_schema
Create Date: 2026-09-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_add_inventory"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("stock_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Integer(), nullable=False, server_default="5"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE",
            name="fk_inventory_product_id_products",
        ),
        sa.CheckConstraint("stock_on_hand >= 0", name="ck_inventory_stock_non_negative"),
        sa.UniqueConstraint("product_id", name="uq_inventory_product_id"),
    )
    op.create_index("ix_inventory_product_id", "inventory", ["product_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="CASCADE",
            name="fk_inventory_movements_product_id_products",
        ),
        sa.CheckConstraint(
            "quantity_change != 0", name="ck_inventory_movements_quantity_change_non_zero"
        ),
    )
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"])
    op.create_index("ix_inventory_movements_created_at", "inventory_movements", ["created_at"])


def downgrade() -> None:
    op.drop_table("inventory_movements")
    op.drop_table("inventory")
