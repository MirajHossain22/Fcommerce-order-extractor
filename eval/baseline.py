"""Conservative regex-only extraction; no model, credentials, or dataset lookup."""

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
    # A comma separates names/phones/products; addresses may contain commas.
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
    text = normalize_digits(message)
    patterns = [
        rf"(?<![\w.+-])(?P<value>{NUMBER})\s*{UNITS}(?!\w)",
        rf"(?<!\w)(?:order|buy|send|deliver|book|want|need)\s*:?\s+(?P<value>{NUMBER})(?!\w)",
        r"(?<!\w)x\s*(?P<value>[0-9]+)(?!\w)",
        r"(?<!\w)(?P<value>ekta|duita|একটা|দুইটা)(?!\w)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return parse_quantity(match.group("value"))
    return None


def product_from_message(message: str) -> str | None:
    labeled = labeled_value(message, "product")
    if labeled:
        return labeled
    text = normalize_digits(message)
    patterns = [
        rf"(?<![\w.+-]){NUMBER}\s*{UNITS}\s+(?P<product>.+?){PRODUCT_END}",
        rf"(?<!\w)(?:order|buy|send|deliver|book|want|need)\s*:?\s+{NUMBER}\s+(?P<product>.+?){PRODUCT_END}",
        rf"(?<!\w)(?:ekta|duita|একটা|দুইটা)\s+(?P<product>.+?){PRODUCT_END}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Digit normalization preserves offsets; retain the original script.
            return message[match.start("product"):match.end("product")].strip() or None
    return None


def extract_baseline(message: str) -> Order:
    """Extract explicit labels and a small set of common order patterns."""
    if re.search(QUESTION, message, re.IGNORECASE):
        return Order(is_order=False)
    labeled_product = labeled_value(message, "product")
    form_order = labeled_product is not None and labeled_value(message, "quantity") is not None
    if not form_order and not re.search(INTENT, message, re.IGNORECASE):
        return Order(is_order=False)

    candidate = labeled_value(message, "phone")
    if candidate is None:
        match = re.search(r"(?<!\w)\+?(?:[0-9][ -]*){8,}[0-9](?!\w)", normalize_digits(message))
        candidate = match.group().strip() if match else None
    phone, warnings = normalize_phone(candidate)
    return Order(
        is_order=True,
        customer_name=labeled_value(message, "customer_name"),
        phone=phone,
        address=labeled_value(message, "address"),
        product=product_from_message(message),
        quantity=quantity_from_message(message),
        notes=labeled_value(message, "notes"),
        warnings=warnings,
    )
