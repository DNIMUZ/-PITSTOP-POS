"""Analytics dashboard returns real aggregates over committed transactions."""
from __future__ import annotations


async def test_dashboard_shape_and_real_numbers(client, make_product, make_sale, admin_headers):
    product = await make_product(sku="ANL-01", price="20.00", stock=5)
    await make_sale(items=[{"product_id": product["id"], "quantity": 2}], discount_rate="10")
    # total = (40.00 - 4.00) * 1.08 = 38.88; stock 5 -> 3 (reorder 5 => low stock)

    resp = await client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()

    assert body["orders_today"] == 1
    assert body["revenue_today"] == "38.88"
    assert body["items_sold_today"] == 2
    assert body["avg_order_value_today"] == "38.88"
    assert isinstance(body["revenue_last_7_days"], list)
    assert body["top_products"][0]["quantity"] == 2
    assert body["top_products"][0]["revenue"] == "40.00"
    low = next(x for x in body["low_stock"] if x["product_id"] == product["id"])
    assert low["stock_on_hand"] == 3


async def test_dashboard_empty_database(client, admin_headers):
    resp = await client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["orders_today"] == 0
    assert body["revenue_today"] == "0.00"
    assert body["items_sold_today"] == 0
    assert body["avg_order_value_today"] == "0.00"
    assert body["top_products"] == []
    assert body["low_stock"] == []
