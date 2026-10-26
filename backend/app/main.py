"""FastAPI endpoints with file-backed SQLite order storage."""

import sqlite3
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError

from app.export import orders_to_csv
from app.extractor import ExtractionError, extract_order
from app.schemas import BatchExtractRequest, ExtractRequest, Order


DEFAULT_DATABASE = Path(__file__).resolve().parents[2] / "orders.sqlite3"


def initialize_database(database: Path) -> None:
    """Create the table without overwriting any saved orders."""
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            "id INTEGER PRIMARY KEY, payload TEXT NOT NULL)"
        )


def save_orders(database: Path, orders: Sequence[Order]) -> None:
    """Save confirmed orders in one transaction using parameterized SQL."""
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.executemany(
            "INSERT INTO orders (payload) VALUES (?)",
            [(order.model_dump_json(),) for order in orders if order.is_order],
        )


def read_orders(database: Path) -> list[Order]:
    """Read validated orders in insertion order."""
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute("SELECT payload FROM orders ORDER BY id").fetchall()
    return [Order.model_validate_json(row[0]) for row in rows]


def extract_messages(messages: Sequence[str]) -> list[Order]:
    """Translate extraction failures to API errors without exposing secrets."""
    try:
        return [extract_order(message) for message in messages]
    except ValidationError:
        raise HTTPException(503, "LLM configuration is missing or invalid.") from None
    except ExtractionError:
        raise HTTPException(502, "Extraction failed; no results from this request were saved.") from None


def create_app(database: Path = DEFAULT_DATABASE) -> FastAPI:
    """Allow tests to use a temporary database without touching real orders."""
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        initialize_database(database)
        yield

    application = FastAPI(title="Fcommerce Order Extractor", lifespan=lifespan)

    @application.post("/extract", response_model=Order)
    def extract(request: ExtractRequest) -> Order:
        orders = extract_messages([request.message])
        save_orders(database, orders)
        return orders[0]

    @application.post("/extract/batch", response_model=list[Order])
    def extract_batch(request: BatchExtractRequest) -> list[Order]:
        orders = extract_messages(request.messages)
        save_orders(database, orders)
        return orders

    @application.get("/orders", response_model=list[Order])
    def get_orders() -> list[Order]:
        return read_orders(database)

    @application.get("/orders/export.csv", response_class=Response)
    def export_orders() -> Response:
        # A UTF-8 BOM helps spreadsheet software recognize Bangla text.
        content = orders_to_csv(read_orders(database)).encode("utf-8-sig")
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
        )

    return application


app = create_app()
