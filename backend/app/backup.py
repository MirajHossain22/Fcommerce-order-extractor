"""Consistent SQLite backups and non-overwriting restores.

Run with PYTHONPATH=backend: python -m app.backup backup|restore SOURCE TARGET
or python -m app.backup verify SOURCE.
"""

import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def verify(path: Path) -> dict[str, int]:
    path = path.resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed")
        required = {"orders", "checkout_sessions", "tracking_links", "seller_sessions"}
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= tables:
            raise ValueError("Not a current order-desk database; migrate it before backing it up")
        count = 0
        for payload, seller, record in connection.execute("SELECT payload, seller_id, record FROM orders"):
            value = json.loads(record)
            if not seller or not isinstance(json.loads(payload), dict) or not all(k in value for k in ("reference", "status", "history", "items", "total_paisa")):
                raise ValueError("Invalid stored order")
            count += 1
        for table in ("checkout_sessions", "tracking_links"):
            if connection.execute(f"SELECT 1 FROM {table} t LEFT JOIN orders o ON o.id=t.order_id WHERE o.id IS NULL LIMIT 1").fetchone():
                raise ValueError("A saved link references a missing order")
        inventory_tables = {"products", "variants", "stock_movements"}
        if tables & inventory_tables:
            if not inventory_tables <= tables:
                raise ValueError("Incomplete inventory schema")
            if connection.execute("SELECT 1 FROM variants v LEFT JOIN products p ON p.id=v.product_id WHERE p.id IS NULL OR v.stock<0 LIMIT 1").fetchone():
                raise ValueError("Invalid catalog stock or product reference")
            if connection.execute("SELECT 1 FROM stock_movements m LEFT JOIN orders o ON o.id=m.order_id LEFT JOIN variants v ON v.id=m.variant_id WHERE o.id IS NULL OR v.id IS NULL OR m.quantity<=0 LIMIT 1").fetchone():
                raise ValueError("Invalid stock movement reference")
        return {"orders": count}


def copy_database(source: Path, target: Path, *, restore: bool = False) -> dict[str, int]:
    source = source.resolve(strict=True)
    target = target.resolve()
    if source == target:
        raise ValueError("Source and destination must be different")
    verify(source)
    # Exclusive creation prevents overwriting live databases or prior backups.
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(target)) as destination:
                original.backup(destination, pages=128)
                if restore:
                    with destination:
                        destination.execute("DELETE FROM seller_sessions")
        return verify(target)
    except BaseException:
        # Only remove the new file this invocation exclusively created.
        target.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("backup", "restore", "verify"))
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command != "verify" and args.target is None:
        parser.error("backup and restore require a new destination path")
    if args.command == "verify" and args.target is not None:
        parser.error("verify accepts only a source path")
    try:
        result = verify(args.source) if args.command == "verify" else copy_database(args.source, args.target, restore=args.command == "restore")
    except (OSError, sqlite3.Error, ValueError, TypeError) as error:
        print(f"{args.command} failed: {error}")
        return 1
    print(json.dumps({"operation": args.command, "verified": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
