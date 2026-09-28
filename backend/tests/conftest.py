"""Pytest fixtures: run against a real PostgreSQL test database.

Environment must point at the test database before any `app` import so the
module-level async engine binds to it.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

os.environ["APP_ENV"] = "testing"
os.environ[
    "DATABASE_URL"
] = "postgresql+asyncpg://pitstop:pitstop_dev_password@localhost:5432/pitstop_test"
os.environ["LOGIN_RATE_LIMIT"] = "20/minute"
os.environ["JWT_SECRET"] = "test-only-secret-4c9f6b2d8e1a7c30f0a5b7d2e9c81f40"
os.environ["TAX_RATE_PERCENT"] = "8.00"

import pytest_asyncio
import sqlalchemy as sa
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from alembic import command
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.database.session import AsyncSessionLocal
from app.database.session import engine as test_engine
from app.main import app
from app.models.user import User

BACKEND_DIR = Path(__file__).resolve().parent.parent

ALL_TABLES = (
    "refund_items",
    "refunds",
    "payments",
    "transaction_items",
    "transactions",
    "inventory_movements",
    "inventory",
    "audit_logs",
    "products",
    "categories",
    "users",
)


def run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(scope="session")
async def migrate() -> None:
    """Apply all Alembic migrations once per test session."""
    await asyncio.to_thread(run_migrations)
    yield


@pytest_asyncio.fixture(autouse=True)
async def clean_between_tests(migrate):
    """Reset every table (and invoice sequences) between tests."""
    yield
    limiter.reset()
    async with test_engine.begin() as conn:
        joined = ", ".join(ALL_TABLES)
        await conn.execute(sa.text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))
        await conn.execute(sa.text("ALTER SEQUENCE txn_no_seq RESTART WITH 1000"))
        await conn.execute(sa.text("ALTER SEQUENCE refund_no_seq RESTART WITH 1000"))


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _add_user(username: str, password: str, full_name: str, role: str) -> User:
    async with AsyncSessionLocal() as session:
        user = User(
            username=username,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(autouse=True)
async def users():
    return {
        "admin": await _add_user("tadmin", "Admin@2026", "Test Admin", "admin"),
        "manager": await _add_user("tmanager", "Manager@2026", "Test Manager", "manager"),
        "cashier": await _add_user("tcashier", "Cashier@2026", "Test Cashier", "cashier"),
    }


@pytest_asyncio.fixture
def login(client):
    async def _login(username: str, password: str) -> dict:
        resp = await client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


@pytest_asyncio.fixture
async def cashier_headers(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "tcashier", "password": "Cashier@2026"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def manager_headers(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "tmanager", "password": "Manager@2026"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "tadmin", "password": "Admin@2026"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
def make_product(client, login):
    """Create a product through the API (manager) and return its dict."""
    async def _make(
        sku: str = "TST-001",
        name: str = "Test Product",
        price: str = "100.00",
        stock: int = 10,
        barcode_field: str | None = None,
    ) -> dict:
        headers = await login("tmanager", "Manager@2026")
        payload = {
            "sku": sku,
            "name": name,
            "barcode": barcode_field or f"BAR-{sku}",
            "unit_price": price,
            "initial_stock": stock,
            "reorder_level": 5,
        }
        resp = await client.post(
            "/api/v1/products",
            headers=headers,
            json=payload,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _make


@pytest_asyncio.fixture
def make_sale(client):
    """Perform a checkout as cashier and return the response."""
    async def _sale(
        items: list[dict],
        discount_rate: str = "0",
        method: str = "cash",
        amount: str | None = None,
        reference: str | None = None,
        headers: dict | None = None,
    ):
        headers = headers or await _login_for()
        return await client.post(
            "/api/v1/transactions",
            headers=headers,
            json={
                "items": items,
                "discount_rate": discount_rate,
                "payment": {"method": method, "amount": amount, "reference": reference},
            },
        )

    async def _login_for():
        resp = await client.post(
            "/api/v1/auth/login", json={"username": "tcashier", "password": "Cashier@2026"}
        )
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _sale
