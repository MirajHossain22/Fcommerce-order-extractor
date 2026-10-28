import pytest

from eval.baseline import extract_baseline, parse_quantity


def test_labeled_english_order() -> None:
    order = extract_baseline(
        "Order 2 TEST_PRODUCT. Name: TEST_CUSTOMER. Phone: 01700-000000. "
        "Address: TEST_ADDRESS."
    )
    assert order.is_order
    assert order.customer_name == "TEST_CUSTOMER"
    assert order.phone == "01700000000"
    assert order.address == "TEST_ADDRESS"
    assert order.product == "TEST_PRODUCT"
    assert order.quantity == 2
    assert order.notes is None
    assert order.warnings == []


def test_mixed_script_order_preserves_text() -> None:
    order = extract_baseline(
        "ভাই ২টা পরীক্ষা পণ্য চাই, নাম: পরীক্ষা_ক্রেতা, "
        "ফোন: ০১৮০০-০০০০০০, ঠিকানা: পরীক্ষা_ঠিকানা।"
    )
    assert order.is_order
    assert order.customer_name == "পরীক্ষা_ক্রেতা"
    assert order.phone == "01800000000"
    assert order.address == "পরীক্ষা_ঠিকানা"
    assert order.product == "পরীক্ষা পণ্য"
    assert order.quantity == 2


@pytest.mark.parametrize(
    "message",
    [
        "hello, কেমন আছেন?",
        "TEST_PRODUCT er price koto?",
        "ei product ta ki stock e ache?",
        "Thanks bhai, product ta bhalo chilo!",
    ],
)
def test_non_orders(message: str) -> None:
    assert extract_baseline(message).model_dump() == {
        "is_order": False,
        "customer_name": None,
        "phone": None,
        "address": None,
        "product": None,
        "quantity": None,
        "notes": None,
        "warnings": [],
    }


def test_invalid_explicit_phone_is_null_with_warning() -> None:
    order = extract_baseline("2 ta TEST_PRODUCT chai, phone 00000")
    assert order.phone is None
    assert len(order.warnings) == 1
    assert "Invalid phone" in order.warnings[0]


def test_missing_fields_remain_null() -> None:
    order = extract_baseline("2 ta TEST_PRODUCT chai")
    assert order.is_order
    assert order.customer_name is None
    assert order.phone is None
    assert order.address is None
    assert order.product == "TEST_PRODUCT"
    assert order.quantity == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [("৫", 5), ("duita", 2), ("একটা", 1), ("0", None), ("-1", None), (None, None)],
)
def test_parse_quantity(value: str | None, expected: int | None) -> None:
    assert parse_quantity(value) == expected
