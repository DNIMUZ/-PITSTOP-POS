"""The most important scenarios: stock validation, money math, atomicity,
concurrency, and transaction listing rules."""
from __future__ import annotations

import asyncio


async def test_health_of_spec_scenario_stock_10_buy_2_equals_8(client, make_product, make_sale):
    product = await make_product(sku="STK-10", price="10.00", stock=10)
    resp = await make_sale(items=[{"product_id": product["id"], "quantity": 2}])
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    assert tx["status"] == "completed"
    assert tx["subtotal"] == "20.00"

    detail = await client.get(
        f"/api/v1/products/{product['id']}", headers=(await _cashier(client))
    )
    assert detail.json()["stock_on_hand"] == 8


async def test_oversell_fails_without_changing_stock(client, make_product, make_sale):
    product = await make_product(sku="STK-03", price="10.00", stock=3)
    resp = await make_sale(items=[{"product_id": product["id"], "quantity": 9}])
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "TRANSACTION_FAILED"
    assert "request_id" in body

    headers = await _cashier(client)
    detail = await client.get(f"/api/v1/products/{product['id']}", headers=headers)
    assert detail.json()["stock_on_hand"] == 3

    listing = await client.get("/api/v1/transactions", headers=headers)
    assert listing.json()["total"] == 0


async def test_discount_tax_and_total_are_server_side_and_exact(
    client, make_product, make_sale
):
    product = await make_product(sku="MATH-01", price="100.00", stock=10)
    resp = await make_sale(
        items=[{"product_id": product["id"], "quantity": 3}],
        discount_rate="10",
    )
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    # subtotal 300.00, discount 10% = 30.00, taxable 270.00,
    # SST 8% = 21.60, total = 291.60
    assert tx["subtotal"] == "300.00"
    assert tx["discount_rate"] == "10.00"
    assert tx["discount_amount"] == "30.00"
    assert tx["tax_rate"] == "8.00"
    assert tx["tax_amount"] == "21.60"
    assert tx["total"] == "291.60"


async def test_cash_tendered_and_change(client, make_product, make_sale):
    product = await make_product(sku="CASH-01", price="50.00", stock=5)
    resp = await make_sale(
        items=[{"product_id": product["id"], "quantity": 1}],
        method="cash",
        amount="100.00",
    )
    assert resp.status_code == 201, resp.text
    tx = resp.json()
    # total = 50.00 * 1.08 = 54.00; tendered 100.00 -> change 46.00
    assert tx["total"] == "54.00"
    assert tx["tendered_amount"] == "100.00"
    assert tx["change_amount"] == "46.00"


async def test_qr_payment_is_recorded_not_gateway_confirmed(client, make_product, make_sale):
    product = await make_product(sku="QR-01", price="25.00", stock=5)
    resp = await make_sale(
        items=[{"product_id": product["id"], "quantity": 1}],
        method="qr",
        reference="QR-DEMO-000184",
    )
    assert resp.status_code == 201, resp.text
    payment = resp.json()["payments"][0]
    assert payment["method"] == "qr"
    assert payment["status"] == "recorded"
    assert payment["transaction_reference"] == "QR-DEMO-000184"


async def test_qr_payment_requires_reference(client, make_product, make_sale):
    product = await make_product(sku="QR-02", price="5.00", stock=5)
    resp = await make_sale(
        items=[{"product_id": product["id"], "quantity": 1}],
        method="qr",
        reference=None,
    )
    assert resp.status_code == 422


async def test_atomic_rollback_when_second_item_insufficient(client, make_product, make_sale):
    a = await make_product(sku="ATOM-A", price="10.00", stock=10)
    b = await make_product(sku="ATOM-B", price="20.00", stock=2)
    resp = await make_sale(
        items=[
            {"product_id": a["id"], "quantity": 2},
            {"product_id": b["id"], "quantity": 9},
        ]
    )
    assert resp.status_code == 409
    headers = await _cashier(client)
    assert (await client.get(f"/api/v1/products/{a['id']}", headers=headers)).json()[
        "stock_on_hand"
    ] == 10
    assert (await client.get(f"/api/v1/products/{b['id']}", headers=headers)).json()[
        "stock_on_hand"
    ] == 2
    assert (await client.get("/api/v1/transactions", headers=headers)).json()["total"] == 0


async def test_concurrent_purchase_of_last_unit(client, make_product, make_sale):
    product = await make_product(sku="RACE-01", price="99.00", stock=1)
    headers_cashier_a = await _cashier(client)
    headers_cashier_b = await _cashier(client)

    responses = await asyncio.gather(
        client.post(
            "/api/v1/transactions",
            headers=headers_cashier_a,
            json={
                "items": [{"product_id": product["id"], "quantity": 1}],
                "discount_rate": "0",
                "payment": {"method": "cash", "amount": "99.00"},
            },
        ),
        client.post(
            "/api/v1/transactions",
            headers=headers_cashier_b,
            json={
                "items": [{"product_id": product["id"], "quantity": 1}],
                "discount_rate": "0",
                "payment": {"method": "card", "reference": "CARD-XYZ"},
            },
        ),
    )

    codes = sorted(r.status_code for r in responses)
    assert codes == [201, 409], [(r.status_code, r.text) for r in responses]
    created = next(r for r in responses if r.status_code == 201)
    failed = next(r for r in responses if r.status_code == 409)
    assert failed.json()["error"] == "TRANSACTION_FAILED"
    assert created.json()["total"] == "106.92"  # 99.00 * 1.08

    detail = await client.get(
        f"/api/v1/products/{product['id']}", headers=headers_cashier_a
    )
    assert detail.json()["stock_on_hand"] == 0


async def test_cashier_sees_only_own_transactions(client, make_product, make_sale, login):
    product = await make_product(sku="VIS-01", price="10.00", stock=20)
    await make_sale(items=[{"product_id": product["id"], "quantity": 1}])

    manager_headers = await login("tmanager", "Manager@2026")
    all_tx = await client.get("/api/v1/transactions", headers=manager_headers)
    assert all_tx.json()["total"] == 1

    cashier_headers = await login("tcashier", "Cashier@2026")
    own = await client.get("/api/v1/transactions", headers=cashier_headers)
    assert own.json()["total"] == 1

    other = await client.get(
        "/api/v1/transactions", headers=await login("tadmin", "Admin@2026")
    )
    assert other.json()["total"] == 1


async def test_transaction_detail_includes_items_and_payment(
    client, make_product, make_sale
):
    product = await make_product(sku="DTL-01", price="15.00", stock=5)
    resp = await make_sale(items=[{"product_id": product["id"], "quantity": 2}])
    tx = resp.json()
    detail = await client.get(
        f"/api/v1/transactions/{tx['id']}", headers=await _cashier(client)
    )
    body = detail.json()
    assert body["transaction_no"] == tx["transaction_no"]
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Test Product"
    assert body["items"][0]["line_total"] == "30.00"
    assert body["payments"][0]["method"] == "cash"
    # money serializes as strings, never floats
    assert isinstance(tx["total"], str)


async def test_checkout_requires_auth(client, make_product):
    product = await make_product(sku="AUTH-1", price="1.00", stock=5)
    resp = await client.post(
        "/api/v1/transactions",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "payment": {"method": "cash"}},
    )
    assert resp.status_code == 401


async def _cashier(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "tcashier", "password": "Cashier@2026"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
