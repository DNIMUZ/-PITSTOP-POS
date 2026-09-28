"""Domain enums stored as strings with CHECK constraints in PostgreSQL."""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"


class TransactionStatus(StrEnum):
    COMPLETED = "completed"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    VOIDED = "voided"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    QR = "qr"
    E_WALLET = "ewallet"


class PaymentStatus(StrEnum):
    """Distinguishes a locally recorded payment from a gateway-confirmed one."""

    RECORDED = "recorded"
    GATEWAY_CONFIRMED = "gateway_confirmed"


class MovementType(StrEnum):
    INITIAL = "initial"
    SALE = "sale"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"
    REFUND = "refund"


class AuditAction(StrEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    TRANSACTION_CREATED = "transaction_created"
    TRANSACTION_REFUNDED = "transaction_refunded"
    INVENTORY_ADJUSTED = "inventory_adjusted"
    PRODUCT_CREATED = "product_created"
    PRODUCT_UPDATED = "product_updated"
    PRODUCT_DEACTIVATED = "product_deactivated"
    CATEGORY_CREATED = "category_created"
    CATEGORY_UPDATED = "category_updated"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
