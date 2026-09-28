"""003_add_transactions: transactions, transaction_items, payments.

Revision ID: 003_add_transactions
Revises: 002_add_inventory
Create Date: 2026-09-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003_add_transactions"
down_revision: str | None = "002_add_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TXN_NO_DEFAULT = sa.text(
    "'TXN-' || lpad(nextval('txn_no_seq')::text, 8, '0')"
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE txn_no_seq")

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "transaction_no",
            sa.String(length=40),
            nullable=False,
            server_default=_TXN_NO_DEFAULT,
        ),
        sa.Column("cashier_id", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "discount_rate", sa.Numeric(precision=5, scale=2),
            nullable=False, server_default="0",
        ),
        sa.Column(
            "discount_amount", sa.Numeric(precision=12, scale=2),
            nullable=False, server_default="0",
        ),
        sa.Column(
            "tax_rate", sa.Numeric(precision=5, scale=2),
            nullable=False, server_default="0",
        ),
        sa.Column(
            "tax_amount", sa.Numeric(precision=12, scale=2),
            nullable=False, server_default="0",
        ),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tendered_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("change_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "status", sa.String(length=30),
            nullable=False, server_default="completed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["cashier_id"], ["users.id"],
            name="fk_transactions_cashier_id_users",
        ),
        sa.CheckConstraint("total >= 0", name="ck_transactions_total_non_negative"),
        sa.CheckConstraint(
            "discount_amount <= subtotal",
            name="ck_transactions_discount_not_exceeding_subtotal",
        ),
        sa.UniqueConstraint("transaction_no", name="uq_transactions_transaction_no"),
    )
    op.create_index("ix_transactions_transaction_no", "transactions", ["transaction_no"])
    op.create_index("ix_transactions_cashier_id", "transactions", ["cashier_id"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])

    op.create_table(
        "transaction_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE",
            name="fk_transaction_items_transaction_id_transactions",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], ondelete="RESTRICT",
            name="fk_transaction_items_product_id_products",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_transaction_items_quantity_positive"),
        sa.CheckConstraint(
            "line_total >= 0", name="ck_transaction_items_line_total_non_negative"
        ),
    )
    op.create_index("ix_transaction_items_transaction_id", "transaction_items", ["transaction_id"])
    op.create_index("ix_transaction_items_product_id", "transaction_items", ["product_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="recorded"
        ),
        sa.Column("transaction_reference", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="CASCADE",
            name="fk_payments_transaction_id_transactions",
        ),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_non_negative"),
    )
    op.create_index("ix_payments_transaction_id", "payments", ["transaction_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("transaction_items")
    op.drop_table("transactions")
    op.execute("DROP SEQUENCE txn_no_seq")
