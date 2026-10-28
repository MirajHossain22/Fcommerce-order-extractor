"""Seller catalog and stock movements inside the order transaction."""
import secrets
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.schemas import Message


class VariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    product: Message = Field(max_length=200)
    size: Message | None = Field(default=None, max_length=80)
    color: Message | None = Field(default=None, max_length=80)
    unit_price_paisa: int = Field(ge=0, le=100000000)
    stock: int = Field(ge=0, le=1000000)


class VariantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=1)
    unit_price_paisa: int = Field(ge=0, le=100000000)
    stock: int = Field(ge=0, le=1000000)
    active: bool = True


def migrate(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, seller_id TEXT NOT NULL, name TEXT NOT NULL, UNIQUE(seller_id, name))")
    connection.execute("CREATE TABLE IF NOT EXISTS variants (id TEXT PRIMARY KEY, product_id TEXT NOT NULL, size TEXT NOT NULL, color TEXT NOT NULL, unit_price_paisa INTEGER NOT NULL CHECK(unit_price_paisa>=0), stock INTEGER NOT NULL CHECK(stock>=0), active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1, UNIQUE(product_id, size, color))")
    connection.execute("CREATE TABLE IF NOT EXISTS stock_movements (order_id INTEGER NOT NULL, variant_id TEXT NOT NULL, event TEXT NOT NULL CHECK(event IN ('sale','restore')), quantity INTEGER NOT NULL CHECK(quantity>0), PRIMARY KEY(order_id, variant_id, event))")


SELECT = "SELECT v.id, p.id, p.name, v.size, v.color, v.unit_price_paisa, v.stock, v.active, v.version FROM variants v JOIN products p ON p.id=v.product_id "


def serialize(row):
    return dict(zip(("variant_id", "product_id", "product", "size", "color", "unit_price_paisa", "stock", "active", "version"),
                    (*row[:3], row[3] or None, row[4] or None, row[5], row[6], bool(row[7]), row[8])))


def get(connection, seller, variant_id):
    row = connection.execute(SELECT + "WHERE p.seller_id=? AND v.id=?", (seller, variant_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Catalog variant not found")
    return serialize(row)


def list_catalog(database: Path, seller: str):
    with closing(sqlite3.connect(database)) as connection:
        return [serialize(row) for row in connection.execute(SELECT + "WHERE p.seller_id=? ORDER BY p.name, v.size, v.color", (seller,))]


def create_variant(database: Path, seller: str, request: VariantCreate):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        product = connection.execute("SELECT id FROM products WHERE seller_id=? AND name=?", (seller, request.product)).fetchone()
        product_id = product[0] if product else secrets.token_hex(16)
        if not product:
            connection.execute("INSERT INTO products VALUES (?, ?, ?)", (product_id, seller, request.product))
        variant_id = secrets.token_hex(16)
        try:
            connection.execute("INSERT INTO variants(id, product_id, size, color, unit_price_paisa, stock) VALUES (?, ?, ?, ?, ?, ?)",
                               (variant_id, product_id, request.size or "", request.color or "", request.unit_price_paisa, request.stock))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "This product size/color already exists. Update its stock instead.") from None
        return get(connection, seller, variant_id)


def update_variant(database: Path, seller: str, variant_id: str, request: VariantUpdate):
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        current = get(connection, seller, variant_id)
        if current["version"] != request.expected_version:
            raise HTTPException(409, "Stock changed. Refresh the catalog before adjusting it.")
        connection.execute("UPDATE variants SET unit_price_paisa=?, stock=?, active=?, version=version+1 WHERE id=?",
                           (request.unit_price_paisa, request.stock, request.active, variant_id))
        return get(connection, seller, variant_id)


def validate_items(connection, seller, items):
    quantities = defaultdict(int)
    for item in items:
        variant_id = item.get("variant_id")
        if not variant_id:
            if item.get("product_id"):
                raise HTTPException(422, "Select a variant for the catalog product")
            continue  # Existing manual line items remain explicitly untracked.
        variant = get(connection, seller, variant_id)
        if not variant["active"]:
            raise HTTPException(409, "A selected product variant is no longer available")
        if any(item.get(key) != variant[key] for key in ("product_id", "product", "size", "color")):
            raise HTTPException(422, "Product details do not match the selected catalog variant")
        quantities[variant_id] += item["quantity"]
    return quantities


def consume(connection, order_id, seller, items):
    quantities = validate_items(connection, seller, items)
    for variant_id, quantity in quantities.items():
        changed = connection.execute("UPDATE variants SET stock=stock-?, version=version+1 WHERE id=? AND stock>=? AND active=1", (quantity, variant_id, quantity))
        if changed.rowcount != 1:
            raise HTTPException(409, "An item is out of stock for this quantity. Contact the seller.")
        connection.execute("INSERT INTO stock_movements VALUES (?, ?, 'sale', ?)", (order_id, variant_id, quantity))


def restore(connection, order_id):
    restored = 0
    for variant_id, quantity in connection.execute("SELECT variant_id, quantity FROM stock_movements WHERE order_id=? AND event='sale'", (order_id,)).fetchall():
        exists = connection.execute("SELECT 1 FROM stock_movements WHERE order_id=? AND variant_id=? AND event='restore'", (order_id, variant_id)).fetchone()
        if exists:
            continue
        connection.execute("UPDATE variants SET stock=stock+?, version=version+1 WHERE id=?", (quantity, variant_id))
        connection.execute("INSERT INTO stock_movements VALUES (?, ?, 'restore', ?)", (order_id, variant_id, quantity))
        restored += quantity
    return restored
