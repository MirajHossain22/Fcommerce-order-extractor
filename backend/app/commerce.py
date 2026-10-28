"""Order lifecycle and checkout storage, independent of AI extraction."""

import hashlib
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.normalize import normalize_phone
from app.schemas import Message, Order
from app import inventory


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    product: Message
    product_id: Message | None = None
    variant_id: Message | None = None
    size: Message | None = None
    color: Message | None = None
    quantity: int = Field(gt=0, le=10000)
    unit_price_paisa: int = Field(ge=0, le=100000000)


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    shop_name: Message = "Online shop"
    customer_name: Message | None = None
    phone: str | None = None
    address: Message | None = None
    items: list[LineItem] = Field(default_factory=list, max_length=100)
    delivery_charge_paisa: int = Field(default=0, ge=0, le=100000000)
    payment_method: Literal["cash_on_delivery"] = "cash_on_delivery"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized, warnings = normalize_phone(value)
        if normalized is None or warnings:
            raise ValueError("Enter a valid Bangladesh mobile number")
        return normalized


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "packed", "shipped", "delivered", "cancelled", "returned"]


class LinkOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expires_in_hours: int = Field(default=24, ge=1, le=168)


class Shipment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    courier_name: Message = Field(max_length=100)
    tracking_reference: Message = Field(max_length=150)


class BuyerConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: int = Field(ge=1)
    customer_name: Message = Field(max_length=200)
    phone: str = Field(max_length=40)
    address: Message = Field(max_length=2000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return Draft.validate_phone(value)


TRANSITIONS = {
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"packed", "cancelled"},
    "packed": {"shipped", "cancelled"},
    "shipped": {"delivered", "returned"},
    "delivered": {"returned"},
    "cancelled": set(),
    "returned": set(),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(draft: Draft, source: str, extracted: Order | None = None) -> dict:
    timestamp = now()
    return {
        "reference": "FC-" + secrets.token_hex(12).upper(),
        "source": source,
        "status": "draft",
        "version": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "history": [{"status": "draft", "at": timestamp}],
        "currency": "BDT",
        **draft.model_dump(),
        "total_paisa": sum(i.quantity * i.unit_price_paisa for i in draft.items) + draft.delivery_charge_paisa,
        "extracted_order": extracted.model_dump() if extracted else None,
    }


def extracted_record(order: Order) -> dict:
    # Product and quantity remain hints until a seller reviews price and variant.
    return record(Draft(customer_name=order.customer_name if order.customer_name and order.customer_name.strip() else None,
                        phone=order.phone,
                        address=order.address if order.address and order.address.strip() else None), "chat", order)


def migrate(connection: sqlite3.Connection, legacy_owner: str) -> None:
    inventory.migrate(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(orders)")}
    if "seller_id" not in columns:
        connection.execute("ALTER TABLE orders ADD COLUMN seller_id TEXT NOT NULL DEFAULT 'legacy'")
        connection.execute("UPDATE orders SET seller_id=?", (legacy_owner,))
    if "record" not in columns:
        connection.execute("ALTER TABLE orders ADD COLUMN record TEXT")
    for row_id, payload in connection.execute("SELECT id, payload FROM orders WHERE record IS NULL").fetchall():
        value = extracted_record(Order.model_validate_json(payload))
        connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row_id))
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS order_reference ON orders(json_extract(record, '$.reference'))")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS checkout_sessions ("
        "token_hash TEXT PRIMARY KEY, order_id INTEGER NOT NULL, version INTEGER NOT NULL, "
        "expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0)"
    )
    session_columns = {row[1] for row in connection.execute("PRAGMA table_info(checkout_sessions)")}
    if "confirmed" not in session_columns:
        connection.execute("ALTER TABLE checkout_sessions ADD COLUMN confirmed INTEGER NOT NULL DEFAULT 0")
    connection.execute("CREATE TABLE IF NOT EXISTS tracking_links (token_hash TEXT PRIMARY KEY, order_id INTEGER NOT NULL UNIQUE)")
    connection.execute("CREATE TABLE IF NOT EXISTS seller_sessions (token_hash TEXT PRIMARY KEY, seller_id TEXT NOT NULL, key_hash TEXT NOT NULL, expires_at TEXT NOT NULL)")


def owned(connection: sqlite3.Connection, reference: str, seller: str) -> tuple[int, dict]:
    row = connection.execute(
        "SELECT id, record FROM orders WHERE seller_id=? AND json_extract(record, '$.reference')=?",
        (seller, reference),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Order not found")
    return row[0], json.loads(row[1])


def list_records(database: Path, seller: str) -> list[dict]:
    with closing(sqlite3.connect(database)) as connection:
        return [json.loads(row[0]) for row in connection.execute("SELECT record FROM orders WHERE seller_id=? ORDER BY id DESC", (seller,))]


def create_draft(database: Path, seller: str, draft: Draft) -> dict:
    value = record(draft, "checkout")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        inventory.validate_items(connection, seller, value["items"])
        connection.execute("INSERT INTO orders(payload, seller_id, record) VALUES (?, ?, ?)",
                           (Order(is_order=True).model_dump_json(), seller, json.dumps(value)))
    return value


def get_record(database: Path, seller: str, reference: str) -> dict:
    with closing(sqlite3.connect(database)) as connection:
        return owned(connection, reference, seller)[1]


def update_draft(database: Path, seller: str, reference: str, draft: Draft) -> dict:
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row_id, value = owned(connection, reference, seller)
        if value["status"] != "draft":
            raise HTTPException(409, "Only drafts can be edited")
        value.update(draft.model_dump())
        inventory.validate_items(connection, seller, value["items"])
        value["total_paisa"] = sum(i.quantity * i.unit_price_paisa for i in draft.items) + draft.delivery_charge_paisa
        value["version"] += 1
        value["updated_at"] = now()
        connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row_id))
        connection.execute("UPDATE checkout_sessions SET revoked=1 WHERE order_id=?", (row_id,))
    return value


def change_status(database: Path, seller: str, reference: str, status: str) -> dict:
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row_id, value = owned(connection, reference, seller)
        if status not in TRANSITIONS[value["status"]]:
            raise HTTPException(409, "Invalid order status transition")
        if status == "confirmed" and not all(value[key] for key in ("items", "customer_name", "phone", "address")):
            raise HTTPException(409, "Review items and complete buyer details before confirming")
        if status == "confirmed":
            inventory.consume(connection, row_id, seller, value["items"])
        if status == "cancelled":
            inventory.restore(connection, row_id)
        value["status"] = status
        value["updated_at"] = now()
        value["history"].append({"status": status, "at": value["updated_at"]})
        connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row_id))
        connection.execute("UPDATE checkout_sessions SET revoked=1 WHERE order_id=?", (row_id,))
    return value


def create_link(database: Path, seller: str, reference: str, hours: int) -> dict:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row_id, value = owned(connection, reference, seller)
        if value["status"] != "draft" or not value["items"]:
            raise HTTPException(409, "Checkout requires a draft with reviewed items")
        connection.execute("UPDATE checkout_sessions SET revoked=1 WHERE order_id=?", (row_id,))
        connection.execute("INSERT INTO checkout_sessions(token_hash, order_id, version, expires_at) VALUES (?, ?, ?, ?)",
                           (hashlib.sha256(token.encode()).hexdigest(), row_id, value["version"], expires))
    # Relative path avoids trusting a caller-controlled Host header.
    return {"checkout_path": "/checkout/" + token, "buyer_path": "/buy/" + token, "expires_at": expires}


def update_shipment(database: Path, seller: str, reference: str, shipment: Shipment) -> dict:
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row_id, value = owned(connection, reference, seller)
        if value["status"] in {"draft", "cancelled"}:
            raise HTTPException(409, "Courier details require a confirmed, non-cancelled order")
        details = shipment.model_dump()
        if value.get("shipment") == details:
            return value
        value["shipment"] = details
        value["updated_at"] = now()
        value["history"].append({"status": value["status"], "event": "courier_updated", "at": value["updated_at"]})
        connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row_id))
    return value


def revoke_links(database: Path, seller: str, reference: str) -> None:
    with closing(sqlite3.connect(database)) as connection, connection:
        row_id, _ = owned(connection, reference, seller)
        connection.execute("UPDATE checkout_sessions SET revoked=1 WHERE order_id=?", (row_id,))


def checkout_summary(database: Path, token: str) -> dict:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT s.version, s.expires_at, s.revoked, o.record FROM checkout_sessions s "
            "JOIN orders o ON o.id=s.order_id WHERE s.token_hash=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Checkout not found")
    value = json.loads(row[3])
    if row[2] or row[1] <= now() or row[0] != value["version"] or value["status"] != "draft":
        raise HTTPException(410, "Checkout is no longer available")
    # Never publish extracted text, buyer contact information, or seller credentials.
    return {"shop_name": value.get("shop_name", "Online shop"), **{key: value[key] for key in ("reference", "version", "items", "currency", "delivery_charge_paisa", "total_paisa", "payment_method")}}


def tracking_token(checkout_token: str) -> str:
    # Domain-separated derivation lets confirmation retries recover the same link
    # without storing either bearer token in plaintext.
    return hashlib.sha256(("tracking-v1:" + checkout_token).encode()).hexdigest()


def buyer_receipt(value: dict, token: str) -> dict:
    return {"tracking_path": "/track/" + tracking_token(token),
            "shop_name": value.get("shop_name", "Online shop"),
            **{key: value[key] for key in ("reference", "items", "currency", "total_paisa", "delivery_charge_paisa", "payment_method")}}


def confirm_checkout(database: Path, token: str, request: BuyerConfirmation) -> dict:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT s.order_id, s.version, s.expires_at, s.revoked, s.confirmed, o.record, o.seller_id "
            "FROM checkout_sessions s JOIN orders o ON o.id=s.order_id WHERE s.token_hash=?", (token_hash,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Checkout not found")
        value = json.loads(row[5])
        if row[4]:
            # Return the original order, never apply different retry details.
            return buyer_receipt(value, token)
        if row[3] or row[2] <= now() or value["status"] != "draft" or row[1] != value["version"]:
            raise HTTPException(410, "Checkout is no longer available. Ask the seller for a new link.")
        if request.version != value["version"]:
            raise HTTPException(409, "The order changed. Reload and review it before confirming.")
        reviewed = Draft.model_validate({key: value[key] for key in Draft.model_fields if key in value})
        total = sum(item.quantity * item.unit_price_paisa for item in reviewed.items) + reviewed.delivery_charge_paisa
        if not reviewed.items or total != value["total_paisa"]:
            raise HTTPException(409, "The seller must review this order before checkout.")
        inventory.consume(connection, row[0], row[6], value["items"])
        value.update(request.model_dump(exclude={"version"}))
        value["status"] = "confirmed"
        value["updated_at"] = now()
        value["history"].append({"status": "confirmed", "at": value["updated_at"], "by": "buyer"})
        connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row[0]))
        connection.execute("UPDATE checkout_sessions SET revoked=1 WHERE order_id=?", (row[0],))
        connection.execute("UPDATE checkout_sessions SET confirmed=1 WHERE token_hash=?", (token_hash,))
        connection.execute("INSERT INTO tracking_links(token_hash, order_id) VALUES (?, ?)",
                           (hashlib.sha256(tracking_token(token).encode()).hexdigest(), row[0]))
        return buyer_receipt(value, token)


def track_order(database: Path, token: str) -> dict:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT o.record FROM tracking_links t JOIN orders o ON o.id=t.order_id WHERE t.token_hash=?",
            (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Tracking link not found")
    value = json.loads(row[0])
    return {"shop_name": value.get("shop_name", "Online shop"), "shipment": value.get("shipment"),
            **{key: value[key] for key in ("reference", "status", "updated_at", "history", "items", "currency", "total_paisa", "delivery_charge_paisa", "payment_method")}}


def checkout_receipt(database: Path, token: str) -> dict:
    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            "SELECT o.record FROM checkout_sessions s JOIN orders o ON o.id=s.order_id "
            "WHERE s.token_hash=? AND s.confirmed=1", (hashlib.sha256(token.encode()).hexdigest(),),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "No confirmed receipt for this checkout")
    return buyer_receipt(json.loads(row[0]), token)


def restock_return(database: Path, seller: str, reference: str) -> dict:
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row_id, value = owned(connection, reference, seller)
        if value["status"] != "returned":
            raise HTTPException(409, "Only returned orders can be restocked manually")
        if inventory.restore(connection, row_id):
            value["restocked"] = True
            value["updated_at"] = now()
            value["history"].append({"status": "returned", "event": "restocked", "at": value["updated_at"]})
            connection.execute("UPDATE orders SET record=? WHERE id=?", (json.dumps(value), row_id))
    return value
