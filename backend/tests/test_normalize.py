import pytest

from app.normalize import normalize_digits, normalize_phone


@pytest.mark.parametrize(
    ("text", "expected"),
    [("০১২৩৪৫৬৭৮৯", "0123456789"), ("পরিমাণ ২, item 3", "পরিমাণ 2, item 3"), ("", "")],
)
def test_normalize_digits(text: str, expected: str) -> None:
    assert normalize_digits(text) == expected


# These are fabricated format-only fixtures, never contact information.
@pytest.mark.parametrize("phone", ["01700-000000", "+880 1700 000000", "8801700000000", "০১৭০০-০০০০০০", " 01700\t000000 "])
def test_normalize_phone(phone: str) -> None:
    assert normalize_phone(phone) == ("01700000000", [])


@pytest.mark.parametrize("phone", ["", "00000", "01200000000", "0170000000", "017000000000", "1700000000", "(+880)1700000000", "+88001700000000", "phone: 01700000000", "০১৭০০abc০০০", "0170000000x"])
def test_invalid_phone_is_flagged(phone: str) -> None:
    number, warnings = normalize_phone(phone)
    assert number is None
    assert len(warnings) == 1
    assert "Invalid phone" in warnings[0]


def test_missing_phone_is_not_invalid() -> None:
    assert normalize_phone(None) == (None, [])


def test_normalization_is_idempotent() -> None:
    phone, _ = normalize_phone("+880 1700-000000")
    assert normalize_phone(phone) == (phone, [])
