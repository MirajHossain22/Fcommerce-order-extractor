from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import sqlite3

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import commerce, inventory
from app.main import create_app
from app.backup import copy_database


AUTH = {"Authorization": "Bearer test-inventory-key"}
VARIANT = {"product": "TEST_SHIRT", "size": "M", "color": "Blue", "unit_price_paisa": 10000, "stock": 5}
BUYER = {"version": 1, "customer_name": "TEST_BUYER", "phone": "01800000001", "address": "TEST_ADDRESS"}


@pytest.fixture
def shop(tmp_path):
    path = tmp_path / "orders.db"
    with TestClient(create_app(path, seller_keys={"test-inventory-key": "seller", "other-key": "other"})) as client:
        yield path, client


def variant(client, stock=5, **changes):
    response = client.post("/seller/catalog", headers=AUTH, json={**VARIANT, "stock": stock, **changes})
    assert response.status_code == 201
    return response.json()


def draft(client, value, quantity=1, items=None):
    item = {key: value[key] for key in ("product", "product_id", "variant_id", "size", "color", "unit_price_paisa")}
    item["quantity"] = quantity
    response = client.post("/seller/orders", headers=AUTH, json={"items": items if items is not None else [item], **{k: v for k, v in BUYER.items() if k != "version"}})
    assert response.status_code == 201
    order = response.json()
    link = client.post(f"/seller/orders/{order['reference']}/checkout-links", headers=AUTH, json={}).json()["checkout_path"]
    return order, link


def stock(client):
    return client.get("/seller/catalog", headers=AUTH).json()[0]["stock"]


def test_seller_catalog_grouping_and_isolation(shop):
    _, client = shop
    first = variant(client)
    second = variant(client, size="L")
    assert first["product_id"] == second["product_id"]
    assert client.post("/seller/catalog", headers=AUTH, json=VARIANT).status_code == 409
    assert client.get("/seller/catalog").status_code == 401
    other = {"Authorization": "Bearer other-key"}
    assert client.get("/seller/catalog", headers=other).json() == []
    body = {"expected_version": 1, "stock": 50, "unit_price_paisa": 1}
    assert client.put('/seller/catalog/' + first['variant_id'], headers=other, json=body).status_code == 404
    malicious = {k: first[k] for k in ("product", "product_id", "variant_id", "size", "color", "unit_price_paisa")}
    assert client.post("/seller/orders", headers=other, json={"items": [{**malicious, "quantity": 1}]}).status_code == 404


def test_confirmation_and_retry_deduct_once_cancellation_restores_once(shop):
    _, client = shop
    value = variant(client)
    order, link = draft(client, value, quantity=2)
    assert stock(client) == 5  # Drafts reserve nothing.
    receipt = client.post(link + "/confirm", json=BUYER)
    assert receipt.status_code == 200 and stock(client) == 3
    assert client.post(link + "/confirm", json=BUYER).json() == receipt.json()
    assert stock(client) == 3
    url = f"/seller/orders/{order['reference']}/status"
    assert client.post(url, headers=AUTH, json={"status": "cancelled"}).status_code == 200
    assert stock(client) == 5
    assert client.post(url, headers=AUTH, json={"status": "cancelled"}).status_code == 409
    assert client.post(link + "/confirm", json=BUYER).status_code == 200
    assert stock(client) == 5


def test_two_buyers_cannot_buy_last_unit(shop):
    database, client = shop
    value = variant(client, stock=1)
    drafts = [draft(client, value) for _ in range(2)]
    def confirm(entry):
        try:
            commerce.confirm_checkout(database, entry[1].split('/')[-1], commerce.BuyerConfirmation(**BUYER))
            return 200
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, drafts)) == [200, 409]
    assert stock(client) == 0
    assert sorted(o["status"] for o in commerce.list_records(database, "seller")) == ["confirmed", "draft"]


def test_duplicate_lines_aggregate_and_failed_order_rolls_back(shop):
    _, client = shop
    value = variant(client, stock=3)
    item = {k: value[k] for k in ("product", "product_id", "variant_id", "size", "color", "unit_price_paisa")}
    _, link = draft(client, value, items=[{**item, "quantity": 2}, {**item, "quantity": 2}])
    assert client.post(link + "/confirm", json=BUYER).status_code == 409
    assert stock(client) == 3
    other = variant(client, stock=0, size="L")
    other_item = {k: other[k] for k in item}
    _, link = draft(client, value, items=[{**item, "quantity": 1}, {**other_item, "quantity": 1}])
    assert client.post(link + "/confirm", json=BUYER).status_code == 409
    rows = client.get('/seller/catalog', headers=AUTH).json()
    assert next(v for v in rows if v['variant_id'] == value['variant_id'])['stock'] == 3


def test_manual_confirmation_and_return_inspection(shop):
    _, client = shop
    value = variant(client, stock=4)
    order, _ = draft(client, value, quantity=2)
    url = f"/seller/orders/{order['reference']}"
    for status in ("confirmed", "packed", "shipped", "returned"):
        assert client.post(url + "/status", headers=AUTH, json={"status": status}).status_code == 200
    assert stock(client) == 2
    first = client.post(url + "/restock", headers=AUTH)
    assert first.status_code == 200 and first.json()["restocked"] is True
    assert stock(client) == 4
    assert client.post(url + "/restock", headers=AUTH).json() == first.json()
    assert stock(client) == 4


def test_stale_stock_adjustment_cannot_undo_sale(shop):
    _, client = shop
    value = variant(client)
    _, link = draft(client, value)
    client.post(link + "/confirm", json=BUYER)
    body = {"expected_version": value["version"], "stock": 5, "unit_price_paisa": 10000}
    assert client.put('/seller/catalog/' + value['variant_id'], headers=AUTH, json=body).status_code == 409
    assert stock(client) == 4


def test_catalog_price_change_preserves_agreed_draft_price(shop):
    _, client = shop
    value = variant(client)
    _, link = draft(client, value)
    body = {"expected_version": 1, "stock": 5, "unit_price_paisa": 25000}
    assert client.put('/seller/catalog/' + value['variant_id'], headers=AUTH, json=body).status_code == 200
    receipt = client.post(link + "/confirm", json=BUYER)
    assert receipt.status_code == 200 and receipt.json()["total_paisa"] == 10000


def test_deactivated_variant_blocks_confirmation(shop):
    _, client = shop
    value = variant(client)
    _, link = draft(client, value)
    body = {"expected_version": 1, "stock": 5, "unit_price_paisa": 10000, "active": False}
    client.put('/seller/catalog/' + value['variant_id'], headers=AUTH, json=body)
    assert client.post(link + "/confirm", json=BUYER).status_code == 409
    assert stock(client) == 5


def test_wrong_variant_identity_and_negative_stock_rejected(shop):
    _, client = shop
    value = variant(client)
    item = {k: value[k] for k in ("product", "product_id", "variant_id", "size", "color", "unit_price_paisa")}
    assert client.post('/seller/orders', headers=AUTH, json={"items": [{**item, "size": "wrong", "quantity": 1}]}).status_code == 422
    assert client.post('/seller/catalog', headers=AUTH, json={**VARIANT, "stock": -1}).status_code == 422


def test_failure_after_stock_write_rolls_back_and_backup_retains_movements(shop, tmp_path):
    source, client = shop
    value = variant(client)
    order, link = draft(client, value)
    with closing(sqlite3.connect(source)) as connection, connection:
        connection.execute("CREATE TRIGGER fail_tracking BEFORE INSERT ON tracking_links BEGIN SELECT RAISE(ABORT, 'failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        client.post(link + "/confirm", json=BUYER)
    assert stock(client) == 5
    with closing(sqlite3.connect(source)) as connection, connection:
        assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
        connection.execute("DROP TRIGGER fail_tracking")
    client.post(link + "/confirm", json=BUYER)
    restored = tmp_path / "restored.db"
    copy_database(source, restored, restore=True)
    commerce.change_status(restored, "seller", order["reference"], "cancelled")
    assert inventory.list_catalog(restored, "seller")[0]["stock"] == 5
    assert stock(client) == 4
