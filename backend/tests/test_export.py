import csv
import io
import json

from app.export import orders_to_csv
from app.schemas import Order


def test_empty_export_has_header() -> None:
    rows = list(csv.reader(io.StringIO(orders_to_csv([]))))
    assert rows == [list(Order.model_fields)]


def test_unicode_quotes_commas_and_newlines_round_trip() -> None:
    order = Order(
        is_order=True,
        product="পরীক্ষা পণ্য",
        address='TEST_ADDRESS, "BLOCK_000"\nTEST_FLOOR',
        phone="01700000000",
        quantity=2,
        warnings=["পরীক্ষা warning, quoted"],
    )
    row = list(csv.DictReader(io.StringIO(orders_to_csv([order]))))[0]
    assert row["product"] == order.product
    assert row["address"] == order.address
    assert row["phone"] == "01700000000"
    assert row["quantity"] == "2"
    assert row["is_order"] == "true"
    assert json.loads(row["warnings"]) == order.warnings


def test_nulls_are_empty_cells_and_rows_keep_order() -> None:
    rows = list(csv.DictReader(io.StringIO(orders_to_csv([
        Order(is_order=True), Order(is_order=False),
    ]))))
    assert [row["is_order"] for row in rows] == ["true", "false"]
    for row in rows:
        for field in ("customer_name", "phone", "address", "product", "quantity", "notes"):
            assert row[field] == ""
        assert row["warnings"] == "[]"
