"""Deterministic regex-only extraction baseline; no model, credentials, or network calls."""

import re

from app.normalize import normalize_digits, normalize_phone
from app.schemas import Order


LABELS = {
    "customer_name": r"name|naam|customer|নাম",
    "phone": r"phone|mobile|number|contact|phn|ph|ফোন|মোবাইল|নাম্বার|নং",
    "address": r"delivery address|address|add|ঠিকানা",
    "product": r"product|পণ্য",
    "quantity": r"quantity|qty|পরিমাণ",
    "notes": r"notes|note|নোট",
}
ALL_LABELS = "|".join(LABELS.values())
WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "ekta": 1, "duita": 2, "একটা": 1, "দুইটা": 2,
    "এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5,
}
NUMBER = r"(?:[0-9]+|" + "|".join(WORDS) + r")"
UNITS = r"(?:pcs?|pieces?|pis|ta|টা|টি|পিস)"
INTENT = r"(?<!\w)(?:order|buy|send|deliver|book|lagbe|chai|nibo|pathai|অর্ডার|লাগবে|চাই|নিব|দিন)(?!\w)"
QUESTION = r"\?|(?<!\w)(?:price|stock|available|koto|ache|thanks|ধন্যবাদ|কত)(?!\w)"
PRODUCT_END = r"(?=\s+(?:to|lagbe|chai|nibo|pathai|order|লাগবে|চাই|নিব|অর্ডার|দিন)(?!\w)|[,.;\n।]|$)"


def labeled_value(message: str, field: str) -> str | None:
    """Copy explicitly labeled text, stopping before punctuation or another label."""
    separator = r"\s*[:：]\s*" if field in ("product", "notes") else r"\s*[:：]?\s*"
    pattern = (
        rf"(?<!\w)(?:{LABELS[field]})(?!\w){separator}"
        rf"(?P<value>.+?)(?=\s*(?:(?:[,;]\s*|\n)(?:{ALL_LABELS})(?!\w)\s*[:：]?|"
        rf"(?<!\w)(?:{ALL_LABELS})(?!\w)\s*[:：])|[.;।]|$)"
    )
    match = re.search(pattern, message, re.IGNORECASE)
    if match is None:
        return None
    value = match.group("value").strip(" ,;\t")
    if field not in ("address", "notes"):
        value = value.split(",", 1)[0].strip()
    return value or None


def parse_quantity(value: str | None) -> int | None:
    if value is None:
        return None
    value = normalize_digits(value).strip().lower()
    if value in WORDS:
        return WORDS[value]
    if re.fullmatch(r"[0-9]+", value):
        number = int(value)
        return number if number > 0 else None
    return None


def quantity_from_message(message: str) -> int | None:
    labeled = labeled_value(message, "quantity")
    if labeled is not None:
        return parse_quantity(labeled)
    normalized = normalize_digits(message)
    match = re.search(rf"\b(?P<qty>{NUMBER})\s*{UNITS}?\s+(?:(?!\b{ALL_LABELS}\b).+?){PRODUCT_END}", normalized, re.IGNORECASE)
    if match:
        return parse_quantity(match.group("qty"))
    suffix = re.search(rf"\b(?P<qty>{NUMBER})\s*{UNITS}\b", normalized, re.IGNORECASE)
    if suffix:
        return parse_quantity(suffix.group("qty"))
    return None


def product_from_message(message: str) -> str | None:
    labeled = labeled_value(message, "product")
    if labeled is not None:
        return labeled
    normalized = normalize_digits(message)
    match = re.search(rf"\b{NUMBER}\s*{UNITS}?\s+(?P<product>(?!\b{ALL_LABELS}\b).+?){PRODUCT_END}", normalized, re.IGNORECASE)
    if match:
        start, end = match.span("product")
        value = message[start:end].strip(" ,;\t")
        return value or None
    fallback = re.search(rf"(?<!\w)(?P<product>(?!\b{ALL_LABELS}\b)[A-Za-z0-9\u0980-\u09FF\s]{{2,60}}?)\s+{INTENT}", message, re.IGNORECASE)
    if fallback:
        value = fallback.group("product").strip(" ,;\t\n")
        words = [w for w in value.split() if w.lower() not in ("ami", "amake", "please", "bhai", "vai", "apnar", "ei")]
        return " ".join(words) or None
    return None


def extract_baseline(message: str) -> Order:
    """Classify and extract order fields using regular expressions."""
    if not message.strip():
        return Order(is_order=False)
    has_intent = re.search(INTENT, message, re.IGNORECASE) is not None
    is_question = re.search(QUESTION, message, re.IGNORECASE) is not None
    phone, phone_warnings = normalize_phone(labeled_value(message, "phone") or re.search(r"(\+?880\s*1[3-9]\d{8}|01[3-9]\d{8})", normalize_digits(message)).group(0) if re.search(r"(\+?880\s*1[3-9]\d{8}|01[3-9]\d{8})", normalize_digits(message)) else None)
    address = labeled_value(message, "address")
    customer_name = labeled_value(message, "customer_name")
    product = product_from_message(message)
    quantity = quantity_from_message(message)
    notes = labeled_value(message, "notes")
    is_order = bool(has_intent and not (is_question and not (phone or address)))
    if not is_order:
        return Order(is_order=False)
    return Order(
        is_order=True,
        customer_name=customer_name,
        phone=phone,
        address=address,
        product=product,
        quantity=quantity,
        notes=notes,
        warnings=phone_warnings,
    )
