"""Refund correctness: money proportional to amount actually paid (tax included),
stock restoration, full vs partial status, and RBAC."""
from __future__ import annotations


async def _refund(client, headers, tx_id, items, reason="Since said so"):
    return await client.post(
        f"/api/v1/transactions/{tx_id}/refund",
        headers=headers,
        json={"transaction_id": tx_id, "items": items, "reason": reason},
    )


async def test_partial_refund_restores_stock_and_is_proportional(
    client, make_product, make_sale, manager_headers
):
    product = await make_product(sku="RF-A", price="10.00", stock=10)
    tx = (await make_sale(items=[{"product_id": product["id"], "quantity": 2}])).json()
    item = tx["items"][0]
    assert tx["total"] == "21.60"  # 20.00 * 1.08

    resp = await _refund(
        client, manager_headers, tx["id"], [{"transaction_item_id": item["id"], "quantity": 1}]
    )
    assert resp.status_code == 201, resp.text
    refund = resp.json()
    assert refund["refund_no"].startswith("RFD-")
    # half of "amount actually paid" (20.00 * 1.08 = 21.60) = 10.80
    assert refund["amount"] == "10.80"

    headers = await _cashier(client)
    stock = (await client.get(f"/api/v1/products/{product['id']}", headers=headers)).json()
    assert stock["stock_on_hand"] == 9
    tx_after = (await client.get(f"/api/v1/transactions/{tx['id']}", headers=headers)).json()
    assert tx_after["status"] == "partially_refunded"


async def test_full_refund_exactly_matches_total_paid(client, make_product, make_sale, manager_headers):
    product = await make_product(sku="RF-B", price="15.00", stock=4)
    tx = (await make_sale(
        items=[{"product_id": product["id"], "quantity": 2}],
        discount_rate="10",
    )).json()
    item = tx["items"][0]
    assert tx["total"] == "29.16"  # (30.00 - 3.00) * 1.08

    resp = await _refund(
        client, manager_headers, tx["id"], [{"transaction_item_id": item["id"], "quantity": 2}]
    )
    assert resp.status_code == 201, resp.text
    refund = resp.json()
    assert refund["amount"] == "29.16"

    headers = await _cashier(client)
    tx_after = (await client.get(f"/api/v1/transactions/{tx['id']}", headers=headers)).json()
    assert tx_after["status"] == "refunded"
    stock = (await client.get(f"/api/v1/products/{product['id']}", headers=headers)).json()
    assert stock["stock_on_hand"] == 4


async def test_cannot_over_refund(client, make_product, make_sale, manager_headers):
    product = await make_product(sku="RF-C", price="8.00", stock=3)
    tx = (await make_sale(items=[{"product_id": product["id"], "quantity": 1}])).json()
    item = tx["items"][0]

    ok = await _refund(
        client, manager_headers, tx["id"], [{"transaction_item_id": item["id"], "quantity": 1}]
    )
    assert ok.status_code == 201

    over = await _refund(
        client, manager_headers, tx["id"], [{"transaction_item_id": item["id"], "quantity": 1}]
    )
    assert over.status_code == 409
    assert over.json()["error"] == "REFUND_FAILED"
    assert (await client.get(f"/api/v1/products/{product['id']}", headers=await _cashier(client))).json()[
        "stock_on_hand"
    ] == 3


async def test_cashier_cannot_refund(client, make_product, make_sale, cashier_headers):
    product = await make_product(sku="RF-D", price="6.00", stock=3)
    tx = (await make_sale(items=[{"product_id": product["id"], "quantity": 1}])).json()
    item = tx["items"][0]
    resp = await _refund(
        client, cashier_headers, tx["id"], [{"transaction_item_id": item["id"], "quantity": 1}]
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "FORBIDDEN"


async def _cashier(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "tcashier", "password": "Cashier@2026"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
