"""Health and version endpoints."""
from __future__ import annotations


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


async def test_health_db_ok(client):
    resp = await client.get("/health/db")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["database"] == "ok"


async def test_version(client):
    resp = await client.get("/api/v1/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "PITSTOP POS"
    assert body["version"]
    assert body["environment"] == "testing"


async def test_unhandled_errors_are_json_envelopes(client, admin_headers):
    resp = await client.get("/api/v1/products/999999", headers=admin_headers)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "NOT_FOUND"
    assert "request_id" in body
    assert "Traceback" not in resp.text
