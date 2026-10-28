import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app import commerce


KEYS = {"test-seller-secret": "shop"}
AUTH = {"Authorization": "Bearer test-seller-secret"}
DRAFT = {"shop_name": "TEST_SHOP", "items": [{"product": "TEST_PRODUCT", "quantity": 2, "size": "M", "color": "Blue", "unit_price_paisa": 50000}], "delivery_charge_paisa": 6000}
BUYER = {"version": 1, "customer_name": "TEST_BUYER", "phone": "+8801800000001", "address": "TEST_ADDRESS"}


@pytest.fixture
def setup(tmp_path):
    database = tmp_path / "orders.db"
    with TestClient(create_app(database, seller_keys=KEYS)) as client:
        order = client.post("/seller/orders", json=DRAFT, headers=AUTH).json()
        link = client.post(f"/seller/orders/{order['reference']}/checkout-links", json={}, headers=AUTH).json()
        yield database, client, order, link


def test_confirm_receipt_retry_and_restart(setup):
    database, client, order, link = setup
    path = link["checkout_path"]
    first = client.post(path + "/confirm", json=BUYER)
    assert first.status_code == 200
    receipt = first.json()
    assert receipt["reference"] == order["reference"]
    assert receipt["total_paisa"] == 106000
    assert "TEST_BUYER" not in first.text and "TEST_ADDRESS" not in first.text
    assert client.post(path + "/confirm", json={**BUYER, "address": "CHANGED"}).json() == receipt
    assert client.get(path + "/receipt").json() == receipt
    with TestClient(create_app(database, seller_keys=KEYS)) as restarted:
        assert restarted.post(path + "/confirm", json=BUYER).json() == receipt
        rows = restarted.get("/seller/orders", headers=AUTH).json()
        assert len(rows) == 1 and rows[0]["status"] == "confirmed"
        assert rows[0]["address"] == "TEST_ADDRESS"
        assert rows[0]["phone"] == "01800000001"
        assert [item["status"] for item in rows[0]["history"]] == ["draft", "confirmed"]


def test_simultaneous_confirmation_creates_one_event(setup):
    database, _, _, link = setup
    token = link["checkout_path"].split("/")[-1]
    request = commerce.BuyerConfirmation(**BUYER)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: commerce.confirm_checkout(database, token, request), range(8)))
    assert all(result == results[0] for result in results)
    value = commerce.list_records(database, "shop")[0]
    assert len(value["history"]) == 2
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tracking_links").fetchone()[0] == 1


@pytest.mark.parametrize("changes", [{"version": 2}, {"customer_name": " "}, {"phone": "123"}, {"address": ""}, {"total_paisa": 1}, {"items": []}])
def test_bad_confirmation_cannot_change_order(setup, changes):
    _, client, order, link = setup
    response = client.post(link["checkout_path"] + "/confirm", json={**BUYER, **changes})
    assert response.status_code == (409 if changes == {"version": 2} else 422)
    value = client.get(f"/seller/orders/{order['reference']}", headers=AUTH).json()
    assert value["status"] == "draft" and value["customer_name"] is None


def test_old_link_cannot_confirm_new_price(setup):
    _, client, order, link = setup
    client.put(f"/seller/orders/{order['reference']}", headers=AUTH, json={**DRAFT, "delivery_charge_paisa": 8000})
    assert client.post(link["checkout_path"] + "/confirm", json=BUYER).status_code == 410
    assert client.get(link["checkout_path"] + "/receipt").status_code == 404


def test_expired_confirmation_and_unknown_token(setup):
    database, client, _, link = setup
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE checkout_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
    assert client.post(link["checkout_path"] + "/confirm", json=BUYER).status_code == 410
    assert client.post("/checkout/unknown/confirm", json=BUYER).status_code == 404


def test_confirmation_rolls_back_if_tracking_write_fails(setup):
    database, client, order, link = setup
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TRIGGER fail_tracking BEFORE INSERT ON tracking_links BEGIN SELECT RAISE(ABORT, 'failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        client.post(link["checkout_path"] + "/confirm", json=BUYER)
    value = client.get(f"/seller/orders/{order['reference']}", headers=AUTH).json()
    assert value["status"] == "draft" and len(value["history"]) == 1
    assert client.get(link["checkout_path"]).status_code == 200


def test_tracking_is_private_and_reflects_seller_status(setup):
    _, client, order, link = setup
    receipt = client.post(link["checkout_path"] + "/confirm", json=BUYER).json()
    track_token = receipt["tracking_path"].split("/")[-1]
    assert track_token != link["checkout_path"].split("/")[-1]
    client.post(f"/seller/orders/{order['reference']}/status", json={"status": "packed"}, headers=AUTH)
    response = client.get("/api/tracking/" + track_token)
    assert response.json()["status"] == "packed"
    assert response.json()["history"][-1]["status"] == "packed"
    assert "TEST_ADDRESS" not in response.text and "TEST_BUYER" not in response.text
    assert client.get("/api/tracking/" + order["reference"]).status_code == 404
    assert client.get("/seller/orders", headers={"Authorization": "Bearer " + track_token}).status_code == 401


def login(client):
    return client.post("/session", json={"key": "test-seller-secret"}, headers={"X-Requested-With": "checkout-app", "Origin": "http://testserver"})


def test_session_cookie_csrf_and_logout(setup):
    database, client, _, _ = setup
    response = login(client)
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    assert "test-seller-secret" not in response.text
    csrf = response.json()["csrf_token"]
    assert client.get("/session").json()["csrf_token"] == csrf
    assert client.get("/seller/orders").status_code == 200
    assert client.post("/seller/orders", json=DRAFT).status_code == 403
    assert client.post("/seller/orders", json=DRAFT, headers={"X-CSRF-Token": csrf, "Origin": "https://attacker.invalid"}).status_code == 403
    assert client.post("/seller/orders", json=DRAFT, headers={"X-CSRF-Token": csrf}).status_code == 201
    cookie = client.cookies.get("seller_session")
    with closing(sqlite3.connect(database)) as connection:
        stored = connection.execute("SELECT token_hash, key_hash FROM seller_sessions").fetchone()
        assert stored[0] != cookie and stored[1] != "test-seller-secret"
    assert client.delete("/session", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/seller/orders").status_code == 401
    assert client.get("/seller/orders", headers={"Cookie": "seller_session=" + cookie}).status_code == 401


def test_session_login_origin_and_key_checks(setup):
    _, client, _, _ = setup
    assert client.post("/session", json={"key": "test-seller-secret"}).status_code == 403
    assert client.post("/session", json={"key": "test-seller-secret"}, headers={"X-Requested-With": "checkout-app", "Origin": "https://attacker.invalid"}).status_code == 403
    assert client.post("/session", json={"key": "wrong"}, headers={"X-Requested-With": "checkout-app"}).status_code == 401


def test_oversized_login_key_is_rejected_without_a_session(setup):
    _, client, _, _ = setup
    response = client.post("/session", json={"key": "x" * 513}, headers={"X-Requested-With": "checkout-app"})
    assert response.status_code == 422
    assert "seller_session" not in response.headers.get("set-cookie", "")


@pytest.mark.parametrize("authorization", ["", "Basic test-seller-secret", "Bearer", "Bearer wrong", "Bearer test-seller-secret extra"])
def test_malformed_authorization_is_rejected(setup, authorization):
    _, client, _, _ = setup
    headers = {"Authorization": authorization} if authorization else {}
    assert client.get("/seller/orders", headers=headers).status_code == 401


def test_expired_session_and_key_revocation(setup):
    database, client, _, _ = setup
    login(client)
    cookie = client.cookies.get("seller_session")
    with TestClient(create_app(database, seller_keys={"replacement-key": "shop"})) as changed:
        assert changed.get("/seller/orders", headers={"Cookie": "seller_session=" + cookie}).status_code == 401
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE seller_sessions SET expires_at='2000-01-01T00:00:00+00:00'")
    assert client.get("/seller/orders").status_code == 401


def test_secure_cookie_on_https(tmp_path):
    with TestClient(create_app(tmp_path / "secure.db", seller_keys=KEYS), base_url="https://testserver") as client:
        response = client.post("/session", json={"key": "test-seller-secret"}, headers={"X-Requested-With": "checkout-app"})
        assert "Secure" in response.headers["set-cookie"]


def test_html_and_assets_are_served_with_security_headers(setup):
    _, client, _, link = setup
    for path in ["/", link["buyer_path"], "/track/test", "/assets/seller.js", "/assets/buyer.js", "/assets/styles.css"]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "Your shop, in order." in client.get("/").text
    assert "অর্ডার নিশ্চিত করুন" in client.get(link["buyer_path"]).text


@pytest.mark.parametrize("path", ["/.env", "/assets/../.env", "/assets/%2e%2e/.env", "/assets/%2e%2e%2f.env"])
def test_static_file_traversal_does_not_expose_environment(setup, path):
    _, client, _, _ = setup
    response = client.get(path)
    assert response.status_code in {404, 405}
    assert "API_KEY" not in response.text
