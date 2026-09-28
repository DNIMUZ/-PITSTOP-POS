"""004_add_refunds: refunds + refund_items.

Revision ID: 004_add_refunds
Revises: 003_add_transactions
Create Date: 2026-09-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_add_refunds"
down_revision: str | None = "003_add_transactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REFUND_NO_DEFAULT = sa.text(
    "'RFD-' || lpad(nextval('refund_no_seq')::text, 8, '0')"
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE refund_no_seq")

    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "refund_no",
            sa.String(length=40),
            nullable=False,
            server_default=_REFUND_NO_DEFAULT,
        ),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("processed_by", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="RESTRICT",
            name="fk_refunds_transaction_id_transactions",
        ),
        sa.ForeignKeyConstraint(
            ["processed_by"], ["users.id"], name="fk_refunds_processed_by_users"
        ),
        sa.CheckConstraint("amount >= 0", name="ck_refunds_amount_non_negative"),
        sa.UniqueConstraint("refund_no", name="uq_refunds_refund_no"),
    )
    op.create_index("ix_refunds_refund_no", "refunds", ["refund_no"])
    op.create_index("ix_refunds_transaction_id", "refunds", ["transaction_id"])
    op.create_index("ix_refunds_processed_by", "refunds", ["processed_by"])
    op.create_index("ix_refunds_created_at", "refunds", ["created_at"])

    op.create_table(
        "refund_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refund_id", sa.Integer(), nullable=False),
        sa.Column("transaction_item_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["refund_id"], ["refunds.id"], ondelete="CASCADE",
            name="fk_refund_items_refund_id_refunds",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_item_id"], ["transaction_items.id"], ondelete="RESTRICT",
            name="fk_refund_items_transaction_item_id_transaction_items",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="RESTRICT",
            name="fk_refund_items_product_id_products",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_refund_items_quantity_positive"),
        sa.CheckConstraint(
            "amount >= 0", name="ck_refund_items_amount_non_negative"
        ),
    )
    op.create_index("ix_refund_items_refund_id", "refund_items", ["refund_id"])
    op.create_index("ix_refund_items_transaction_item_id", "refund_items", ["transaction_item_id"])
    op.create_index("ix_refund_items_product_id", "refund_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("refund_items")
    op.drop_table("refunds")
    op.execute("DROP SEQUENCE refund_no_seq")
