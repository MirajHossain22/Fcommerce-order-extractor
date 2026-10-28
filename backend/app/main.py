"""FastAPI endpoints with file-backed SQLite order storage."""

import sqlite3
import json
import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.export import orders_to_csv
from app.extractor import ExtractionError, extract_order
from app.schemas import BatchExtractRequest, ExtractRequest, Order
from app import commerce, inventory
from app.seller_auth import seller_auth, mount_sessions


DEFAULT_DATABASE = Path(__file__).resolve().parents[2] / "orders.sqlite3"


def initialize_database(database: Path, legacy_owner: str = "legacy") -> None:
    """Create the table without overwriting any saved orders."""
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )
        commerce.migrate(connection, legacy_owner)


def save_orders(database: Path, orders: Sequence[Order], seller_id: str = "legacy") -> None:
    """Save extraction results as unconfirmed drafts in one transaction."""
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executemany(
            "INSERT INTO orders (payload, seller_id, record) VALUES (?, ?, ?)",
            [(order.model_dump_json(), seller_id, json.dumps(commerce.extracted_record(order))) for order in orders if order.is_order],
        )


def read_orders(database: Path, seller_id: str = "legacy") -> list[Order]:
    """Read validated orders in insertion order."""
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute("SELECT payload FROM orders WHERE seller_id=? AND json_extract(record, '$.source')='chat' ORDER BY id", (seller_id,)).fetchall()
    return [Order.model_validate_json(row[0]) for row in rows]


def extract_messages(messages: Sequence[str]) -> list[Order]:
    """Translate extraction failures to API errors without exposing secrets."""
    try:
        return [extract_order(message) for message in messages]
    except ValidationError:
        raise HTTPException(503, "LLM configuration is missing or invalid.") from None
    except ExtractionError:
        raise HTTPException(502, "Extraction failed; no results from this request were saved.") from None


def create_app(database: Path | None = None, *, seller_keys: dict[str, str] | None = None, legacy_owner: str = "legacy") -> FastAPI:
    """Allow tests to use a temporary database without touching real orders."""
    if database is None:
        database = Path(os.environ.get("DATABASE_PATH") or DEFAULT_DATABASE).expanduser().resolve()
    database = database.expanduser().resolve()
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(database, legacy_owner)
        yield

    application = FastAPI(title="Fcommerce Order Extractor", lifespan=lifespan)
    authenticate = seller_auth(seller_keys, database)
    mount_sessions(application, database, authenticate)

    @application.get("/healthz", include_in_schema=False)
    def health():
        try:
            with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
                connection.execute("SELECT id FROM orders LIMIT 1").fetchone()
        except sqlite3.Error:
            raise HTTPException(503, "Storage unavailable") from None
        return {"status": "ok"}

    @application.middleware("http")
    async def prevent_sensitive_caching(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @application.post("/extract", response_model=Order)
    def extract(request: ExtractRequest, seller: str = Depends(authenticate)) -> Order:
        orders = extract_messages([request.message])
        save_orders(database, orders, seller)
        return orders[0]

    @application.post("/extract/batch", response_model=list[Order])
    def extract_batch(request: BatchExtractRequest, seller: str = Depends(authenticate)) -> list[Order]:
        orders = extract_messages(request.messages)
        save_orders(database, orders, seller)
        return orders

    @application.get("/orders", response_model=list[Order])
    def get_orders(seller: str = Depends(authenticate)) -> list[Order]:
        return read_orders(database, seller)

    @application.get("/orders/export.csv", response_class=Response)
    def export_orders(seller: str = Depends(authenticate)) -> Response:
        # A UTF-8 BOM helps spreadsheet software recognize Bangla text.
        content = orders_to_csv(read_orders(database, seller)).encode("utf-8-sig")
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
        )

    @application.post("/seller/orders", status_code=201)
    def create_draft(request: commerce.Draft, seller: str = Depends(authenticate)):
        return commerce.create_draft(database, seller, request)

    @application.get("/seller/catalog")
    def catalog(seller: str = Depends(authenticate)):
        return inventory.list_catalog(database, seller)

    @application.post("/seller/catalog", status_code=201)
    def add_variant(request: inventory.VariantCreate, seller: str = Depends(authenticate)):
        return inventory.create_variant(database, seller, request)

    @application.put("/seller/catalog/{variant_id}")
    def edit_variant(variant_id: str, request: inventory.VariantUpdate, seller: str = Depends(authenticate)):
        return inventory.update_variant(database, seller, variant_id, request)

    @application.post("/seller/orders/{reference}/restock")
    def restock(reference: str, seller: str = Depends(authenticate)):
        return commerce.restock_return(database, seller, reference)

    @application.get("/seller/orders")
    def list_drafts(seller: str = Depends(authenticate)):
        return commerce.list_records(database, seller)

    @application.get("/seller/orders/{reference}")
    def get_draft(reference: str, seller: str = Depends(authenticate)):
        return commerce.get_record(database, seller, reference)

    @application.put("/seller/orders/{reference}")
    def edit_draft(reference: str, request: commerce.Draft, seller: str = Depends(authenticate)):
        return commerce.update_draft(database, seller, reference, request)

    @application.post("/seller/orders/{reference}/status")
    def update_status(reference: str, request: commerce.StatusChange, seller: str = Depends(authenticate)):
        return commerce.change_status(database, seller, reference, request.status)

    @application.put("/seller/orders/{reference}/shipment")
    def shipment(reference: str, request: commerce.Shipment, seller: str = Depends(authenticate)):
        return commerce.update_shipment(database, seller, reference, request)

    @application.post("/seller/orders/{reference}/checkout-links", status_code=201)
    def checkout_link(reference: str, request: commerce.LinkOptions, seller: str = Depends(authenticate)):
        return commerce.create_link(database, seller, reference, request.expires_in_hours)

    @application.delete("/seller/orders/{reference}/checkout-links", status_code=204)
    def revoke_checkout(reference: str, seller: str = Depends(authenticate)):
        commerce.revoke_links(database, seller, reference)
        return Response(status_code=204)

    @application.get("/checkout/{token}")
    def checkout(token: str):
        return commerce.checkout_summary(database, token)

    @application.post("/checkout/{token}/confirm")
    def confirm(token: str, request: commerce.BuyerConfirmation):
        return commerce.confirm_checkout(database, token, request)

    @application.get("/checkout/{token}/receipt")
    def receipt(token: str):
        return commerce.checkout_receipt(database, token)

    @application.get("/api/tracking/{token}")
    def tracking(token: str):
        return commerce.track_order(database, token)

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    application.mount("/assets", StaticFiles(directory=frontend), name="assets")

    @application.get("/", include_in_schema=False)
    def seller_page():
        return FileResponse(frontend / "seller.html")

    @application.get("/buy/{token}", include_in_schema=False)
    @application.get("/track/{token}", include_in_schema=False)
    def buyer_page(token: str):
        return FileResponse(frontend / "buyer.html")

    return application


app = create_app()
