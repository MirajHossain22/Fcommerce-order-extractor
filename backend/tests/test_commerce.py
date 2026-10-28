import json
import sqlite3
from contextlib import closing
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app, initialize_database, read_orders
from app.schemas import Order


KEYS = {"seller-a-secret": "seller-a", "seller-b-secret": "seller-b"}
AUTH = {"Authorization": "Bearer seller-a-secret"}
OTHER = {"Authorization": "Bearer seller-b-secret"}
DRAFT = {
    "customer_name": "TEST_BUYER", "phone": "+8801800000001", "address": "TEST_ADDRESS",
    "items": [{"product": "TEST_SHIRT", "size": "M", "color": "Blue", "quantity": 2, "unit_price_paisa": 35050}],
    "delivery_charge_paisa": 6000,
}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "orders.db", seller_keys=KEYS)) as client:
        yield client


def draft(client, data=None):
    response = client.post("/seller/orders", json=DRAFT if data is None else data, headers=AUTH)
    assert response.status_code == 201
    return response.json()


def link(client, reference):
    response = client.post(f"/seller/orders/{reference}/checkout-links", json={}, headers=AUTH)
    assert response.status_code == 201
    return response.json()["checkout_path"]


def test_migration_preserves_payload_reference_and_owner(tmp_path):
    database = tmp_path / "old.db"
    old = Order(is_order=True, product="TEST_PRODUCT", customer_name=" ", quantity=None)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        connection.execute("INSERT INTO orders(payload) VALUES (?)", (old.model_dump_json(),))
    initialize_database(database, "seller-a")
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        first = client.get("/seller/orders", headers=AUTH).json()[0]
        assert first["status"] == "draft"
        assert first["items"] == []
        assert first["extracted_order"] == old.model_dump()
        assert first["customer_name"] is None
        assert client.get("/seller/orders", headers=OTHER).json() == []
    initialize_database(database, "seller-b")
    assert read_orders(database, "seller-a") == [old]
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        assert client.get("/seller/orders", headers=AUTH).json()[0] == first


@pytest.mark.parametrize("path", ["/orders", "/orders/export.csv", "/seller/orders"])
def test_all_order_reads_require_auth(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401


@pytest.mark.parametrize("path,body", [("/extract", {"message": "test"}), ("/extract/batch", {"messages": ["test"]})])
def test_extraction_requires_auth_before_provider_call(client, path, body):
    with patch("app.main.extract_order") as extract:
        assert client.post(path, json=body).status_code == 401
        extract.assert_not_called()


def test_unconfigured_seller_access_fails_closed(tmp_path):
    with TestClient(create_app(tmp_path / "orders.db", seller_keys={})) as client:
        assert client.get("/orders").status_code == 503


def test_seller_isolation_including_legacy_export(client):
    value = draft(client)
    url = "/seller/orders/" + value["reference"]
    assert client.get(url, headers=OTHER).status_code == 404
    assert client.put(url, json=DRAFT, headers=OTHER).status_code == 404
    assert client.post(url + "/status", json={"status": "cancelled"}, headers=OTHER).status_code == 404
    assert client.post(url + "/checkout-links", json={}, headers=OTHER).status_code == 404
    assert client.delete(url + "/checkout-links", headers=OTHER).status_code == 404
    with patch("app.main.extract_order", return_value=Order(is_order=True, product="PRIVATE_PRODUCT")):
        assert client.post("/extract", json={"message": "test"}, headers=AUTH).status_code == 200
    assert client.get("/orders", headers=OTHER).json() == []
    assert "PRIVATE_PRODUCT" not in client.get("/orders/export.csv", headers=OTHER).text
    assert len(client.get("/seller/orders", headers=AUTH).json()) == 2


def test_total_phone_normalization_and_public_privacy(client):
    value = draft(client)
    assert value["total_paisa"] == 76100
    assert value["phone"] == "01800000001"
    response = client.get(link(client, value["reference"]))
    assert response.status_code == 200
    assert response.json()["total_paisa"] == 76100
    assert "TEST_BUYER" not in response.text and "TEST_ADDRESS" not in response.text
    assert "phone" not in response.json() and "extracted_order" not in response.json()
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_links_rotate_revoke_and_invalidate_on_edit(client):
    value = draft(client)
    url = "/seller/orders/" + value["reference"]
    first = link(client, value["reference"])
    second = link(client, value["reference"])
    assert client.get(first).status_code == 410
    updated = client.put(url, json={**DRAFT, "delivery_charge_paisa": 100}, headers=AUTH)
    assert updated.json()["version"] == 2
    assert updated.json()["total_paisa"] == 70200
    assert client.get(second).status_code == 410
    third = link(client, value["reference"])
    assert client.delete(url + "/checkout-links", headers=AUTH).status_code == 204
    assert client.get(third).status_code == 410
    assert client.get("/checkout/not-a-real-token").status_code == 404


def test_link_expiry_and_token_not_stored_plaintext(tmp_path):
    database = tmp_path / "orders.db"
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        path = link(client, draft(client)["reference"])
        with closing(sqlite3.connect(database)) as connection, connection:
            stored = connection.execute("SELECT token_hash FROM checkout_sessions").fetchone()[0]
            assert path.split("/")[-1] != stored
            connection.execute("UPDATE checkout_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
        assert client.get(path).status_code == 410


def test_lifecycle_freezes_confirmed_details_and_persists(tmp_path):
    database = tmp_path / "orders.db"
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        value = draft(client)
        url = "/seller/orders/" + value["reference"]
        checkout = link(client, value["reference"])
        assert client.post(url + "/status", json={"status": "shipped"}, headers=AUTH).status_code == 409
        for status in ("confirmed", "packed", "shipped", "delivered", "returned"):
            result = client.post(url + "/status", json={"status": status}, headers=AUTH)
            assert result.status_code == 200
            assert result.json()["status"] == status
        assert client.get(checkout).status_code == 410
        assert client.put(url, json={**DRAFT, "items": []}, headers=AUTH).status_code == 409
        assert client.post(url + "/status", json={"status": "confirmed"}, headers=AUTH).status_code == 409
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        value = client.get(url, headers=AUTH).json()
        assert value["total_paisa"] == 76100
        assert [event["status"] for event in value["history"]] == ["draft", "confirmed", "packed", "shipped", "delivered", "returned"]


def test_incomplete_draft_cannot_confirm_or_share(client):
    value = draft(client, {})
    url = "/seller/orders/" + value["reference"]
    assert client.post(url + "/status", json={"status": "confirmed"}, headers=AUTH).status_code == 409
    assert client.post(url + "/checkout-links", json={}, headers=AUTH).status_code == 409
    assert client.post(url + "/status", json={"status": "cancelled"}, headers=AUTH).status_code == 200


@pytest.mark.parametrize("data", [
    {**DRAFT, "total_paisa": 1},
    {**DRAFT, "phone": "invalid"},
    {**DRAFT, "delivery_charge_paisa": -1},
    {**DRAFT, "items": [{"product": "test", "quantity": 0, "unit_price_paisa": 100}]},
    {**DRAFT, "items": [{"product": "test", "quantity": 1, "unit_price_paisa": 1.5}]},
    {**DRAFT, "seller_id": "seller-b"},
])
def test_invalid_drafts_cannot_tamper_with_money_or_owner(client, data):
    assert client.post("/seller/orders", json=data, headers=AUTH).status_code == 422
    assert client.get("/seller/orders", headers=AUTH).json() == []


@pytest.mark.parametrize("data", [
    {**DRAFT, "shop_name": "x" * 201},
    {**DRAFT, "customer_name": "x" * 201},
    {**DRAFT, "address": "x" * 2001},
    {**DRAFT, "items": [{"product": "x" * 301, "quantity": 1, "unit_price_paisa": 100}]},
    {**DRAFT, "items": [{"product": "test", "size": "x" * 81, "quantity": 1, "unit_price_paisa": 100}]},
])
def test_oversized_draft_fields_are_rejected(client, data):
    assert client.post("/seller/orders", json=data, headers=AUTH).status_code == 422
    assert client.get("/seller/orders", headers=AUTH).json() == []
