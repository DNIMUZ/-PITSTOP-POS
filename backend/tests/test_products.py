"""Products: CRUD, search, pagination, barcode lookup, RBAC."""
from __future__ import annotations


async def test_create_and_list_products(client, make_product, cashier_headers):
    created = await make_product(sku="APX-999", price="149.00", stock=12)
    assert created["sku"] == "APX-999"
    assert created["stock_on_hand"] == 12
    assert created["barcode"] == "BAR-APX-999"

    listed = await client.get(
        "/api/v1/products?page=1&page_size=25", headers=cashier_headers
    )
    body = listed.json()
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["total"] >= 1
    names = [p["name"] for p in body["items"]]
    assert "Test Product" in names


async def test_search_products_server_side(client, make_product, cashier_headers):
    await make_product(sku="SRC-01", name="Apex Racing Helmet", price="10.00")
    await make_product(sku="SRC-02", name="Titan GP Visor", price="20.00")

    resp = await client.get(
        "/api/v1/products", params={"q": "helmet"}, headers=cashier_headers
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Apex Racing Helmet"


async def test_lookup_by_barcode(client, make_product, cashier_headers):
    product = await make_product(sku="BAR-01", barcode_field="BARCODE2026", price="55.00")
    resp = await client.get(
        "/api/v1/products/lookup/BARCODE2026", headers=cashier_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]
    assert resp.json()["unit_price"] == "55.00"

    resp = await client.get(
        "/api/v1/products/lookup/UNKNOWN-BARCODE", headers=cashier_headers
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "NOT_FOUND"


async def test_lookup_by_sku_fallback(client, make_product, cashier_headers):
    product = await make_product(sku="SKU-LOOK", barcode_field=None, price="30.00")
    resp = await client.get(
        "/api/v1/products/lookup/SKU-LOOK", headers=cashier_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]


async def test_duplicate_sku_rejected(client, make_product, manager_headers):
    await make_product(sku="DUP-01")
    resp = await client.post(
        "/api/v1/products",
        headers=manager_headers,
        json={
            "sku": "DUP-01",
            "name": "Another",
            "unit_price": "1.00",
            "initial_stock": 1,
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "CONFLICT"


async def test_cashier_cannot_create_product(client, cashier_headers):
    resp = await client.post(
        "/api/v1/products",
        headers=cashier_headers,
        json={"sku": "HACK-01", "name": "Nope", "unit_price": "1.00", "initial_stock": 1},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "FORBIDDEN"


async def test_pagination_shapes(client, make_product, cashier_headers):
    for i in range(5):
        await make_product(sku=f"PAG-{i}", name=f"Page Product {i}", price="1.00")
    resp = await client.get(
        "/api/v1/products", params={"page": 1, "page_size": 2}, headers=cashier_headers
    )
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["page_size"] == 2
    assert body["total"] >= 5


async def test_products_require_auth(client):
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 401
