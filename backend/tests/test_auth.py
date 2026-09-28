"""Authentication and login rate limiting."""
from __future__ import annotations


async def test_login_success_and_me(client, users, login):
    headers = await login("tcashier", "Cashier@2026")
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "tcashier"
    assert body["role"] == "cashier"
    assert "hashed_password" not in body


async def test_login_wrong_password(client, users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "tcashier", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "UNAUTHORIZED"
    assert "Traceback" not in resp.text


async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "whatever-123"},
    )
    assert resp.status_code == 401


async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"] == "UNAUTHORIZED"


async def test_me_rejects_bad_token(client, users):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401


async def test_login_rate_limited(client, users):
    # 25 rapid bad logins: the last ones must be 429 RATE_LIMITED.
    responses = []
    for _ in range(25):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"username": "tcashier", "password": "bad-password"},
        )
        responses.append(resp.status_code)
    assert 429 in responses
    limited = [r for r in responses if r == 429]
    assert limited, "expected at least one rate-limited response"


async def test_inactive_user_cannot_login(client, users):

    from app.core.security import hash_password
    from app.database.session import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        user = User(
            username="suspended",
            full_name="Suspended User",
            hashed_password=hash_password("Password123"),
            role="cashier",
            is_active=False,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "suspended", "password": "Password123"},
    )
    assert resp.status_code == 401
