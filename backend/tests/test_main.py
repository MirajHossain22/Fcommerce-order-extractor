import csv
import io
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.extractor import ExtractionError
from app.main import create_app, initialize_database, read_orders, save_orders
from app.schemas import Order


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(tmp_path / "orders.sqlite3", seller_keys={"test-key": "legacy"}), headers={"Authorization": "Bearer test-key"}) as test_client:
        yield test_client


def test_empty_database_and_export(client: TestClient) -> None:
    assert client.get("/orders").json() == []
    exported = client.get("/orders/export.csv")
    assert exported.status_code == 200
    assert list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig")))) == [list(Order.model_fields)]


def test_extract_saves_order_and_preserves_nulls(client: TestClient) -> None:
    order = Order(is_order=True, product="পরীক্ষা পণ্য", quantity=2)
    with patch("app.main.extract_order", return_value=order) as llm:
        result = client.post("/extract", json={"message": "পরীক্ষা পণ্য ২টা চাই"})
    assert result.status_code == 200
    assert result.json() == order.model_dump()
    assert result.json()["customer_name"] is None
    assert result.json()["phone"] is None
    assert result.json()["address"] is None
    assert client.get("/orders").json() == [order.model_dump()]
    llm.assert_called_once_with("পরীক্ষা পণ্য ২টা চাই")


def test_non_order_returned_without_saving(client: TestClient) -> None:
    with patch("app.main.extract_order", return_value=Order(is_order=False)):
        result = client.post("/extract", json={"message": "hello"})
    assert result.status_code == 200
    assert result.json()["is_order"] is False
    assert client.get("/orders").json() == []


def test_batch_returns_input_order_and_saves_only_orders(client: TestClient) -> None:
    orders = [Order(is_order=True, quantity=2), Order(is_order=False), Order(is_order=True)]
    with patch("app.main.extract_order", side_effect=orders) as llm:
        result = client.post("/extract/batch", json={"messages": ["2 ta chai", "hello", "order chai"]})
    assert result.status_code == 200
    assert result.json() == [order.model_dump() for order in orders]
    assert client.get("/orders").json() == [orders[0].model_dump(), orders[2].model_dump()]
    assert [call.args[0] for call in llm.call_args_list] == ["2 ta chai", "hello", "order chai"]


def test_failed_batch_saves_nothing_and_keeps_existing_orders(client: TestClient) -> None:
    existing = Order(is_order=True, product="TEST_EXISTING")
    with patch("app.main.extract_order", return_value=existing):
        client.post("/extract", json={"message": "TEST_EXISTING chai"})
    with patch("app.main.extract_order", side_effect=[Order(is_order=True), ExtractionError("FAKE_SECRET")]):
        result = client.post("/extract/batch", json={"messages": ["order chai", "another order chai"]})
    assert result.status_code == 502
    assert "FAKE_SECRET" not in result.text
    assert client.get("/orders").json() == [existing.model_dump()]


def test_failed_single_extraction_does_not_save(client: TestClient) -> None:
    with patch("app.main.extract_order", side_effect=ExtractionError("FAKE_SECRET")):
        result = client.post("/extract", json={"message": "order chai"})
    assert result.status_code == 502
    assert "FAKE_SECRET" not in result.text
    assert client.get("/orders").json() == []


def test_configuration_error_is_sanitized(client: TestClient) -> None:
    with pytest.raises(ValidationError) as invalid:
        Settings(provider="", model="test", api_key="FAKE_SECRET")
    with patch("app.main.extract_order", side_effect=invalid.value):
        result = client.post("/extract", json={"message": "order chai"})
    assert result.status_code == 503
    assert "FAKE_SECRET" not in result.text


@pytest.mark.parametrize(("endpoint", "body"), [
    ("/extract", {}),
    ("/extract", {"message": ""}),
    ("/extract", {"message": " \n "}),
    ("/extract", {"message": 12}),
    ("/extract", {"message": None}),
    ("/extract", {"message": "hello", "extra": True}),
    ("/extract/batch", {"messages": []}),
    ("/extract/batch", {"messages": "hello"}),
    ("/extract/batch", {"messages": ["valid", " "]}),
    ("/extract/batch", {"messages": [False]}),
])
def test_invalid_requests_never_call_llm(client: TestClient, endpoint: str, body: dict[str, object]) -> None:
    with patch("app.main.extract_order") as llm:
        result = client.post(endpoint, json=body)
    assert result.status_code == 422
    llm.assert_not_called()
    assert client.get("/orders").json() == []


@pytest.mark.parametrize(("endpoint", "body"), [
    ("/extract", {"message": "x" * 10_001}),
    ("/extract/batch", {"messages": ["test"] * 51}),
])
def test_oversized_extraction_requests_never_call_llm(client: TestClient, endpoint: str, body: dict[str, object]) -> None:
    with patch("app.main.extract_order") as llm:
        result = client.post(endpoint, json=body)
    assert result.status_code == 422
    llm.assert_not_called()


def test_csv_download_includes_saved_unicode_and_warnings(client: TestClient) -> None:
    order = Order(is_order=True, product="পরীক্ষা পণ্য", address='TEST_ADDRESS, "000"\nTEST_BLOCK', warnings=["Invalid phone"])
    with patch("app.main.extract_order", return_value=order):
        client.post("/extract", json={"message": "পরীক্ষা পণ্য চাই"})
    result = client.get("/orders/export.csv")
    assert result.status_code == 200
    assert result.headers["content-type"] == "text/csv; charset=utf-8"
    assert result.headers["content-disposition"] == 'attachment; filename="orders.csv"'
    assert result.content.startswith(b"\xef\xbb\xbf")
    row = list(csv.DictReader(io.StringIO(result.content.decode("utf-8-sig"))))[0]
    assert row["product"] == order.product
    assert row["address"] == order.address
    assert row["phone"] == ""
    assert json.loads(row["warnings"]) == order.warnings


def test_orders_persist_across_app_restarts(tmp_path: Path) -> None:
    database = tmp_path / "orders.sqlite3"
    order = Order(is_order=True, customer_name="TEST_CUSTOMER")
    with TestClient(create_app(database, seller_keys={"test-key": "legacy"}), headers={"Authorization": "Bearer test-key"}) as first:
        with patch("app.main.extract_order", return_value=order):
            assert first.post("/extract", json={"message": "order chai"}).status_code == 200
    with TestClient(create_app(database, seller_keys={"test-key": "legacy"}), headers={"Authorization": "Bearer test-key"}) as second:
        assert second.get("/orders").json() == [order.model_dump()]


def test_sql_text_is_stored_as_data(tmp_path: Path) -> None:
    database = tmp_path / "orders.sqlite3"
    initialize_database(database)
    order = Order(is_order=True, notes="TEST_NOTE'); DROP TABLE orders; --")
    save_orders(database, [order, Order(is_order=False)])
    assert read_orders(database) == [order]


def test_storage_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    database = tmp_path / "orders.sqlite3"
    initialize_database(database)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "CREATE TRIGGER reject_second BEFORE INSERT ON orders "
            "WHEN (SELECT COUNT(*) FROM orders) >= 1 "
            "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        save_orders(database, [Order(is_order=True), Order(is_order=True)])
    assert read_orders(database) == []
