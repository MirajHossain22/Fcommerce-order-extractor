import pytest
from pydantic import ValidationError

from app.schemas import Order


def test_missing_fields_remain_null_in_json() -> None:
    order = Order(is_order=True)
    assert order.model_dump() == {
        "is_order": True, "customer_name": None, "phone": None,
        "address": None, "product": None, "quantity": None,
        "notes": None, "warnings": [],
    }
    assert '"quantity":null' in order.model_dump_json()


def test_non_order_is_supported() -> None:
    assert Order(is_order=False).is_order is False


def test_explicit_order_values_round_trip() -> None:
    order = Order(is_order=True, customer_name="TEST_CUSTOMER", phone="01700000000", address="TEST_ADDRESS", product="TEST_PRODUCT", quantity=2)
    assert Order.model_validate_json(order.model_dump_json()) == order


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "2"])
def test_quantity_must_be_positive_integer(quantity: object) -> None:
    with pytest.raises(ValidationError):
        Order.model_validate({"is_order": True, "quantity": quantity})


def test_warnings_are_independent() -> None:
    first = Order(is_order=True)
    first.warnings.append("Invalid phone")
    assert Order(is_order=True).warnings == []


@pytest.mark.parametrize("data", [{}, {"is_order": "true"}, {"is_order": True, "unknown": 1}, {"is_order": True, "phone": "00000"}])
def test_rejects_invalid_schema(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Order.model_validate(data)
