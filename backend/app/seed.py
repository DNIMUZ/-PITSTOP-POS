"""Demo seeder: `python -m app.seed`

Creates a realistic, fully paid-down demo database:
- Admin / Manager / Cashier users (passwords are hashed, documented in README)
- 6 categories, 36 fictional motorsport products with barcodes/SKUs/stock
- ~30 days of sample transactions with payments, inventory movements and audit logs

Safe to run on a fresh development database. Idempotent: no-ops when a seeded
user already exists.
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.enums import (
    AuditAction,
    MovementType,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from app.models.inventory import ProductInventory, StockMovement
from app.models.product import Product
from app.models.refund import Refund, RefundItem
from app.models.transaction import Payment, Transaction, TransactionItem
from app.models.user import User
from app.services.money import compute_totals, money

logger = logging.getLogger("app.seed")

SEED_USERS = [
    {
        "username": "admin",
        "password": "Admin@2026",
        "full_name": "Aidan Ridhwan",
        "role": UserRole.ADMIN,
        "email": "admin@pitstop.dev",
    },
    {
        "username": "manager",
        "password": "Manager@2026",
        "full_name": "Mira Tan",
        "role": UserRole.MANAGER,
        "email": "manager@pitstop.dev",
    },
    {
        "username": "cashier",
        "password": "Cashier@2026",
        "full_name": "Rizwan Khalid",
        "role": UserRole.CASHIER,
        "email": "cashier@pitstop.dev",
    },
]

CATEGORIES = [
    ("Hats & Caps", "Team caps, snapbacks and race hats"),
    ("Apparel", "Polos, tees, hoodies and jackets"),
    ("Gloves", "Racing and technical gloves"),
    ("Accessories", "Lanyards, bottles, phone cases and more"),
    ("Collectibles", "Die-casts, mini helmets and wall art"),
    ("Kid's Line", "Junior apparel and collectibles"),
]

# (sku, name, category, price, stock, reorder)
PRODUCTS = [
    ("APX-101", "Apex Racing Team Cap", "Hats & Caps", "79.90", 42, 10),
    ("APX-102", "Velocity Motorsport Snapback", "Hats & Caps", "89.00", 28, 10),
    ("APX-103", "Titan GP Base Cap", "Hats & Caps", "69.90", 120, 15),
    ("APX-104", "Redline Racing Switchback Cap", "Hats & Caps", "84.00", 4, 10),
    ("APX-105", "Pitstop Precision Racing Cap", "Hats & Caps", "99.00", 60, 12),
    ("APX-201", "Apex Racing Dry-Tech Polo", "Apparel", "129.00", 33, 10),
    ("APX-202", "Velocity Motorsport Race Tee", "Apparel", "109.00", 55, 12),
    ("APX-203", "Titan GP Crew Tee", "Apparel", "99.90", 6, 10),
    ("APX-204", "Redline Racing Hoodie", "Apparel", "189.00", 24, 8),
    ("APX-205", "Apex Racing Team Jacket", "Apparel", "249.00", 15, 5),
    ("APX-206", "Pitstop Performance Windbreaker", "Apparel", "199.00", 18, 6),
    ("APX-301", "Titan GP Pro Driving Gloves", "Gloves", "159.00", 30, 8),
    ("APX-302", "Apex Racing Technical Gloves", "Gloves", "149.00", 3, 8),
    ("APX-303", "Redline Racing Kid Gloves", "Gloves", "89.00", 50, 10),
    ("APX-304", "Velocity Motorsport Half-Finger Gloves", "Gloves", "119.00", 22, 6),
    ("APX-305", "Pitstop Apex Racing Balaclava", "Gloves", "59.00", 70, 12),
    ("APX-401", "Titan GP Keychain Set", "Accessories", "29.90", 200, 25),
    ("APX-402", "Apex Racing Lanyard", "Accessories", "15.00", 150, 20),
    ("APX-403", "Velocity Motorsport Phone Case", "Accessories", "49.90", 80, 15),
    ("APX-404", "Redline Racing Water Bottle", "Accessories", "35.00", 90, 15),
    ("APX-405", "Pitstop Racing Umbrella", "Accessories", "45.00", 40, 10),
    ("APX-406", "Apex Racing Cap Clip", "Accessories", "19.90", 130, 20),
    ("APX-407", "Titan GP Cap Shield", "Accessories", "12.00", 300, 40),
    ("APX-408", "Redline Racing Scarf", "Accessories", "59.90", 0, 8),
    ("APX-409", "Apex Racing Socks (3-pack)", "Accessories", "39.90", 75, 15),
    ("APX-410", "Velocity Motorsport Cargo Cap", "Hats & Caps", "94.00", 26, 8),
    ("APX-501", "Titan GP Polo Shirt", "Apparel", "124.00", 44, 10),
    ("APX-502", "Redline Kids Race Tee", "Kid's Line", "79.90", 38, 10),
    ("APX-503", "Apex Kids Collector Helmet", "Kid's Line", "149.00", 12, 4),
    ("APX-504", "Velocity Kids Trucker Cap", "Kid's Line", "69.00", 20, 6),
    ("APX-505", "Titan GP Mini Helmet Replica", "Collectibles", "199.00", 9, 4),
    ("APX-506", "Apex Racing Die-Cast Car", "Collectibles", "89.00", 16, 6),
    ("APX-507", "Redline Racing Flag Set", "Collectibles", "25.00", 5, 8),
    ("APX-508", "Pitstop Racing Wall Poster", "Collectibles", "24.90", 48, 12),
    ("APX-509", "Apex Racing Insulated Tumbler", "Accessories", "69.00", 35, 10),
    ("APX-510", "Velocity Motorsport Backpack", "Accessories", "149.00", 11, 5),
]

_REF_PREFIX = {
    "cash": "CASH",
    "card": "CARD",
    "qr": "QR",
    "ewallet": "EW",
}


def _days_ago(days: int, hour: int, minute: int, now: datetime) -> datetime:
    day = now - timedelta(days=days)
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


async def seed() -> None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(User.id).limit(1))
        if existing:
            logger.warning("database already seeded; skipping")
            return

        categories: dict[str, Category] = {}
        for name, description in CATEGORIES:
            category = Category(name=name, description=description)
            session.add(category)
            categories[name] = category
        await session.flush()

        product_list: list[Product] = []
        stock_map: dict[int, int] = {}
        reorder_map: dict[int, int] = {}
        for index, (sku, name, category, price, stock, reorder) in enumerate(
            PRODUCTS, start=1
        ):
            product = Product(
                sku=sku,
                name=name,
                barcode=f"PPS{index:06d}",
                category_id=categories[category].id,
                unit_price=Decimal(price),
                cost_price=money(Decimal(price) * Decimal("0.6")),
                image_url=f"/products/{sku.lower()}.svg",
                description=f"{name} - original motorsport design (fictional brand).",
                is_active=stock != 0,
            )
            session.add(product)
            product_list.append(product)
            stock_map[product.id if product.id is not None else len(product_list)] = stock
            reorder_map[product.id if product.id is not None else len(product_list)] = reorder
        await session.flush()

        # Re-map after flush so ids are authoritative (index 4 = stock, 5 = reorder).
        stock_map = {p.id: s for p, s in zip(product_list, [r[4] for r in PRODUCTS], strict=True)}
        reorder_map = {
            p.id: r for p, r in zip(product_list, [r[5] for r in PRODUCTS], strict=True)
        }

        for product in product_list:
            session.add(
                ProductInventory(
                    product_id=product.id,
                    stock_on_hand=stock_map[product.id],
                    reorder_level=reorder_map[product.id],
                )
            )

        for user_data in SEED_USERS:
            session.add(
                User(
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    role=user_data["role"].value,
                )
            )
        await session.flush()

        users = (await session.execute(select(User).order_by(User.id))).scalars().all()
        admin = next(u for u in users if u.role == UserRole.ADMIN.value)
        manager = next(u for u in users if u.role == UserRole.MANAGER.value)
        sellers = [
            u
            for u in users
            if u.role
            in (UserRole.ADMIN.value, UserRole.MANAGER.value, UserRole.CASHIER.value)
        ]

        settings = get_settings()
        rng = random.Random(42)
        transactions_created = 0

        def _pick(qty: int) -> list[tuple[Product, int]]:
            chosen: dict[int, int] = {}
            for product in rng.sample(product_list, rng.randint(1, 4)):
                chosen[product.id] = qty
            return [(next(p for p in product_list if p.id == pid), n) for pid, n in chosen.items()]

        for day_offset in range(30, -1, -1):
            count = 18 if day_offset == 0 else rng.randint(8, 14)
            for _ in range(count):
                transactions_created += 1
                items = _pick(rng.randint(1, 3))
                subtotal = sum(money(p.unit_price * n) for p, n in items)
                discount_rate = Decimal(rng.choice(["0", "0", "0", "5", "10"]))
                discount_amount, tax_amount, total = compute_totals(
                    subtotal, discount_rate, settings.tax_rate_decimal
                )
                method = rng.choice([m.value for m in PaymentMethod])
                tendered = (
                    total + Decimal(rng.choice(["0.00", "0.00", "0.50", "1.00"]))
                    if method == "cash"
                    else total
                )
                when = _days_ago(day_offset, rng.randint(9, 20), rng.randint(0, 59), now)

                transaction = Transaction(
                    cashier_id=rng.choice(sellers).id,
                    subtotal=money(subtotal),
                    discount_rate=money(discount_rate),
                    discount_amount=discount_amount,
                    tax_rate=settings.tax_rate_decimal,
                    tax_amount=tax_amount,
                    total=total,
                    tendered_amount=tendered,
                    change_amount=money(tendered - total) if method == "cash" else None,
                    status="completed",
                    created_at=when,
                )
                session.add(transaction)
                await session.flush()

                for product, qty in items:
                    session.add(
                        TransactionItem(
                            transaction_id=transaction.id,
                            product_id=product.id,
                            product_name=product.name,
                            unit_price=product.unit_price,
                            quantity=qty,
                            line_total=money(product.unit_price * qty),
                        )
                    )
                inventory_rows = {
                    row.product_id: row
                    for row in (
                        await session.execute(
                            select(ProductInventory).where(
                                ProductInventory.product_id.in_([p.id for p, _ in items])
                            )
                        )
                    ).scalars()
                }
                for product, qty in items:
                    inv = inventory_rows.get(product.id)
                    if inv is None or inv.stock_on_hand < qty:
                        continue
                    inv.stock_on_hand -= qty
                    session.add(
                        StockMovement(
                            product_id=product.id,
                            quantity_change=-qty,
                            reason=MovementType.SALE.value,
                            reference_type="transaction",
                            reference_id=transaction.id,
                        )
                    )

                session.add(
                    Payment(
                        transaction_id=transaction.id,
                        method=method,
                        amount=tendered,
                        status=PaymentStatus.RECORDED.value,
                        transaction_reference=(
                            f"{_REF_PREFIX[method]}-{100000 + transactions_created}"
                        ),
                    )
                )
                session.add(
                    AuditLog(
                        user_id=transaction.cashier_id,
                        action=AuditAction.TRANSACTION_CREATED.value,
                        entity_type="transaction",
                        entity_id=transaction.id,
                        details={"transaction_no": transaction.transaction_no},
                    )
                )

        # Two realistic partial refunds for status variety.
        refundable = (
            await session.execute(
                select(Transaction)
                .where(Transaction.total == Transaction.tendered_amount)
                .order_by(Transaction.created_at.desc())
                .limit(40)
            )
        ).scalars().all()
        for tx in refundable[:2]:
            item = (
                (
                    await session.execute(
                        select(TransactionItem).where(
                            TransactionItem.transaction_id == tx.id
                        ).limit(1)
                    )
                )
                .scalars()
                .first()
            )
            if item is None:
                continue
            refund = Refund(
                transaction_id=tx.id,
                processed_by=manager.id,
                amount=item.line_total,
                reason="Demo refund - customer returned item",
            )
            session.add(refund)
            await session.flush()
            session.add(
                RefundItem(
                    refund_id=refund.id,
                    transaction_item_id=item.id,
                    product_id=item.product_id,
                    quantity=1,
                    amount=item.line_total,
                )
            )
            inv = await session.scalar(
                select(ProductInventory).where(
                    ProductInventory.product_id == item.product_id
                )
            )
            if inv is not None:
                inv.stock_on_hand += 1
            tx.status = "partially_refunded"
            session.add(
                AuditLog(
                    user_id=manager.id,
                    action=AuditAction.TRANSACTION_REFUNDED.value,
                    entity_type="transaction",
                    entity_id=tx.id,
                    details={"refund_no": refund.refund_no, "amount": str(item.line_total)},
                )
            )

        session.add(
            AuditLog(
                user_id=admin.id,
                action="system_seeded",
                entity_type="system",
                details={"products": len(product_list), "transactions": transactions_created},
            )
        )
        await session.commit()

        product_total = await session.scalar(select(func.count(Product.id)))
        tx_total = await session.scalar(select(func.count(Transaction.id)))
        logger.info(
            "seed complete",
            extra={"products": product_total, "transactions": tx_total, "users": len(users)},
        )
        print(
            f"Seed complete: {product_total} products, {tx_total} transactions, "
            f"{len(users)} users."
        )


async def main() -> None:
    settings = get_settings()
    logger.info(
        "starting seed",
        extra={"environment": settings.APP_ENV, "db": settings.DATABASE_URL},
    )
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
