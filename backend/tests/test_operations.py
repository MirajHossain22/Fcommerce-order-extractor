import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import commerce
from app.backup import copy_database, verify
from app.main import create_app, initialize_database
from app.serve import build_app


KEY = "synthetic-operations-key-long-enough-123"
AUTH = {"Authorization": "Bearer " + KEY}
DRAFT = {"shop_name": "TEST_SHOP", "items": [{"product": "TEST_PRODUCT", "quantity": 1, "unit_price_paisa": 9900}]}
BUYER = {"version": 1, "customer_name": "TEST_BUYER", "phone": "01800000001", "address": "TEST_ADDRESS"}
SHIPMENT = {"courier_name": "TEST_COURIER", "tracking_reference": "TEST_PARCEL_001"}


@pytest.fixture
def shop(tmp_path):
    database = tmp_path / "orders.db"
    with TestClient(create_app(database, seller_keys={KEY: "seller", "other-key": "other"})) as client:
        order = client.post("/seller/orders", headers=AUTH, json=DRAFT).json()
        url = "/seller/orders/" + order["reference"]
        link = client.post(url + "/checkout-links", headers=AUTH, json={}).json()["checkout_path"]
        yield database, client, url, link


def test_courier_lifecycle_privacy_and_repeat_submission(shop):
    database, client, url, link = shop
    assert client.put(url + "/shipment", headers=AUTH, json=SHIPMENT).status_code == 409
    receipt = client.post(link + "/confirm", json=BUYER).json()
    result = client.put(url + "/shipment", headers=AUTH, json=SHIPMENT)
    assert result.status_code == 200
    value = result.json()
    assert value["status"] == "confirmed" and value["total_paisa"] == 9900
    assert value["history"][-1]["event"] == "courier_updated"
    assert client.put(url + "/shipment", headers=AUTH, json=SHIPMENT).json() == value
    tracking = "/api/tracking/" + receipt["tracking_path"].split("/")[-1]
    assert client.get(tracking).json()["shipment"] == SHIPMENT
    assert "TEST_ADDRESS" not in client.get(tracking).text
    assert client.put(url + "/shipment", headers={"Authorization": "Bearer other-key"}, json=SHIPMENT).status_code == 404
    assert client.put(url + "/shipment", json=SHIPMENT).status_code == 401
    with TestClient(create_app(database, seller_keys={KEY: "seller"})) as restarted:
        assert restarted.get(tracking).json()["shipment"] == SHIPMENT
    client.post(url + "/status", headers=AUTH, json={"status": "cancelled"})
    assert client.put(url + "/shipment", headers=AUTH, json=SHIPMENT).status_code == 409


@pytest.mark.parametrize("body", [{}, {**SHIPMENT, "courier_name": " "}, {**SHIPMENT, "tracking_reference": "x" * 151}, {**SHIPMENT, "courier_url": "javascript:alert(1)"}])
def test_bad_courier_details_rejected(shop, body):
    _, client, url, link = shop
    client.post(link + "/confirm", json=BUYER)
    assert client.put(url + "/shipment", headers=AUTH, json=body).status_code == 422


def test_backup_restore_roundtrip_preserves_links_but_revokes_login(shop, tmp_path):
    source, client, url, link = shop
    receipt = client.post(link + "/confirm", json=BUYER).json()
    client.put(url + "/shipment", headers=AUTH, json=SHIPMENT)
    login = client.post("/session", headers={"X-Requested-With": "checkout-app"}, json={"key": KEY})
    assert login.status_code == 200
    cookie = client.cookies.get("seller_session")
    backup, restored = tmp_path / "backup.db", tmp_path / "restored.db"
    assert copy_database(source, backup) == {"orders": 1}
    assert copy_database(backup, restored, restore=True) == {"orders": 1}
    assert verify(source) == {"orders": 1}
    with TestClient(create_app(restored, seller_keys={KEY: "seller"})) as other:
        assert other.get(url, headers=AUTH).json()["shipment"] == SHIPMENT
        assert other.get(link + "/receipt").json() == receipt
        assert other.post(link + "/confirm", json=BUYER).json() == receipt
        assert other.get("/seller/orders", headers={"Cookie": "seller_session=" + cookie}).status_code == 401
        tracking = "/api/tracking/" + receipt["tracking_path"].split("/")[-1]
        assert other.get(tracking).json()["status"] == "confirmed"
    # Taking a backup does not invalidate current production sessions.
    assert client.get("/session").status_code == 200


def test_backup_captures_committed_wal_data(tmp_path):
    source = tmp_path / "wal.db"
    initialize_database(source)
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        commerce.create_draft(source, "seller", commerce.Draft(**DRAFT))
        target = tmp_path / "snapshot.db"
        assert copy_database(source, target) == {"orders": 1}
        assert commerce.list_records(target, "seller")[0]["shop_name"] == "TEST_SHOP"


def test_backup_never_overwrites_or_creates_missing_source(shop, tmp_path):
    source, _, _, _ = shop
    occupied = tmp_path / "occupied.db"
    occupied.write_bytes(b"keep this file")
    with pytest.raises(FileExistsError):
        copy_database(source, occupied)
    assert occupied.read_bytes() == b"keep this file"
    with pytest.raises(ValueError):
        copy_database(source, source)
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        copy_database(missing, tmp_path / "target.db")
    assert not missing.exists()


def test_backup_rejects_corruption_and_orphan_links(tmp_path):
    source = tmp_path / "corrupt.db"
    source.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        copy_database(source, tmp_path / "target.db")
    assert not (tmp_path / "target.db").exists()
    valid = tmp_path / "invalid-links.db"
    initialize_database(valid)
    with closing(sqlite3.connect(valid)) as connection, connection:
        connection.execute("INSERT INTO tracking_links VALUES ('hash', 999)")
    with pytest.raises(ValueError, match="missing order"):
        verify(valid)


def configure(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "deployed.db"))
    monkeypatch.setenv("ALLOWED_HOSTS", "orders.example.test")
    monkeypatch.setenv("SELLER_API_KEYS", json.dumps({KEY: "seller"}))


def test_pilot_configuration_health_and_https_cookie(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    with TestClient(build_app(), base_url="https://orders.example.test") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/healthz", headers={"Host": "attacker.invalid"}).status_code == 400
        response = client.post("/session", json={"key": KEY}, headers={"X-Requested-With": "checkout-app", "Origin": "https://orders.example.test"})
        assert response.status_code == 200 and "Secure" in response.headers["set-cookie"]
        assert client.post("/seller/orders", json=DRAFT, headers={"X-CSRF-Token": response.json()["csrf_token"]}).status_code == 201
    assert (tmp_path / "deployed.db").exists()


def test_render_hostname_configures_trusted_host(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    monkeypatch.delenv("ALLOWED_HOSTS")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "synthetic-pilot.onrender.com")
    with TestClient(build_app(), base_url="https://synthetic-pilot.onrender.com") as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/healthz", headers={"Host": "attacker.invalid"}).status_code == 400


def test_render_blueprint_has_persistent_single_instance():
    blueprint = (Path(__file__).resolve().parents[2] / "render.yaml").read_text(encoding="utf-8")
    assert "runtime: docker" in blueprint
    assert "region: singapore" in blueprint
    assert "numInstances: 1" in blueprint
    assert "healthCheckPath: /healthz" in blueprint
    assert "value: /data/orders.sqlite3" in blueprint
    assert "mountPath: /data" in blueprint
    assert blueprint.count("sync: false") == 2


@pytest.mark.parametrize("name,value", [("DATABASE_PATH", "relative.db"), ("ALLOWED_HOSTS", ""), ("ALLOWED_HOSTS", "*"), ("ALLOWED_HOSTS", "https://example.test"), ("SELLER_API_KEYS", "{}"), ("SELLER_API_KEYS", '{"short":"seller"}')])
def test_pilot_configuration_fails_early(monkeypatch, tmp_path, name, value):
    configure(monkeypatch, tmp_path)
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        build_app()


def test_health_reports_missing_storage_without_recreating_it(shop):
    source, client, _, _ = shop
    source.unlink()
    assert client.get("/healthz").status_code == 503
    assert not source.exists()
