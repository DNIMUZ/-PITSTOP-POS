"""Money arithmetic shared by all financial services.

All monetary values are Python Decimal. The only rounding applied is
ROUND_HALF_UP to two decimal places, applied once at each total line.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def money(value: Decimal | str | int) -> Decimal:
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def compute_totals(
    subtotal: Decimal,
    discount_rate: Decimal,
    tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return (discount_amount, tax_amount, total)."""
    subtotal = money(subtotal)
    discount_amount = money(subtotal * discount_rate / Decimal("100"))
    taxable = subtotal - discount_amount
    tax_amount = money(taxable * tax_rate / Decimal("100"))
    total = money(taxable + tax_amount)
    return discount_amount, tax_amount, total
