"""Normalize explicit source values without guessing missing information."""

import re


BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
PHONE_PATTERN = re.compile(r"01[3-9][0-9]{8}")


def normalize_digits(text: str) -> str:
    """Convert Bangla digits while preserving all other characters."""
    return text.translate(BANGLA_DIGITS)


def normalize_phone(phone: str | None) -> tuple[str | None, list[str]]:
    """Return a validated phone and warnings; only specified cleanup is allowed."""
    if phone is None:
        return None, []

    cleaned = re.sub(r"[\s-]", "", normalize_digits(phone))
    if cleaned.startswith("+880"):
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("880"):
        cleaned = "0" + cleaned[3:]

    if PHONE_PATTERN.fullmatch(cleaned):
        return cleaned, []
    return None, ["Invalid phone: expected a Bangladeshi number matching ^01[3-9]\\d{8}$."]
