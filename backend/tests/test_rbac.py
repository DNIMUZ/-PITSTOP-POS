"""Role-based access control matrix across all protected endpoints."""
from __future__ import annotations


async def test_role_matrix(client, make_product, make_sale, cashier_headers, manager_headers, admin_headers):
    product = await make_product(sku="RBAC-1", price="10.00", stock=10)
    tx = (await make_sale(items=[{"product_id": product["id"], "quantity": 1}])).json()
    item = tx["items"][0]

    async def status_of(headers, method, path, json_body=None):
        kwargs = {"headers": headers}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = await getattr(client, method)(path, **kwargs)
        return resp.status_code

    # Analytics: admin and manager only.
    assert await status_of(admin_headers, "get", "/api/v1/analytics/dashboard") == 200
    assert await status_of(manager_headers, "get", "/api/v1/analytics/dashboard") == 200
    assert await status_of(cashier_headers, "get", "/api/v1/analytics/dashboard") == 403

    # Refunds: manager+ only.
    refund_body = {"transaction_id": tx["id"], "items": [{"transaction_item_id": item["id"], "quantity": 1}]}
    assert await status_of(manager_headers, "post", f"/api/v1/transactions/{tx['id']}/refund", refund_body) == 201
    assert await status_of(cashier_headers, "post", f"/api/v1/transactions/{tx['id']}/refund", refund_body) == 403

    # Inventory adjustments: manager+ only.
    adjust = {"product_id": product["id"], "quantity_change": 1, "note": "stocktake"}
    assert await status_of(manager_headers, "post", "/api/v1/inventory/adjust", adjust) == 200
    assert await status_of(cashier_headers, "post", "/api/v1/inventory/adjust", adjust) == 403

    # Users (invite / list): admin only.
    invite = {"username": "newname", "full_name": "New", "password": "Password123", "role": "cashier"}
    assert await status_of(admin_headers, "post", "/api/v1/users", invite) == 201
    assert await status_of(manager_headers, "post", "/api/v1/users", invite) == 403
    assert await status_of(admin_headers, "get", "/api/v1/users") == 200
    assert await status_of(manager_headers, "get", "/api/v1/users") == 403

    # Product creation: manager+ only.
    prod = {"sku": "RBAC-2", "name": "No", "unit_price": "1.00", "initial_stock": 1}
    assert await status_of(manager_headers, "post", "/api/v1/products", prod) == 201
    assert await status_of(cashier_headers, "post", "/api/v1/products", prod) == 403

    # Sales: any authenticated role.
    sale = {"items": [{"product_id": product["id"], "quantity": 1}], "payment": {"method": "cash"}}
    assert await status_of(cashier_headers, "post", "/api/v1/transactions", sale) == 201
