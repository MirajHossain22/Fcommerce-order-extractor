"""Seed script for Credosis Phase 02 demo and testing.

Populates realistic Bangladeshi F-commerce store data:
- Shop: "Dacca Loom"
- Catalog variants (Panjabi, Saree, Earbuds, Wallet) with realistic prices & stock
- Low stock indicators (<= 5 units)
- Orders across all key statuses: delivered, shipped (with courier ref), packed, confirmed, draft (with active checkout link), and chat-extracted draft.

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --reset
    python scripts/seed_demo.py --db custom.sqlite3 --seller custom-shop
"""

import argparse
import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend directory is in python path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import initialize_database
from app import commerce, inventory
from app.commerce import Draft, LineItem, StatusChange, Shipment, BuyerConfirmation
from app.inventory import VariantCreate
from app.schemas import Order


DEMO_SELLER = "local-shop"
DEMO_KEY = "demo-seller-key"
DEFAULT_DB = ROOT / "orders.sqlite3"


def ensure_seller_key_in_env(env_path: Path, demo_key: str = DEMO_KEY, seller_id: str = DEMO_SELLER) -> None:
    """Check if SELLER_API_KEYS is configured, and offer instructions if missing."""
    if not env_path.exists():
        print(f"[!] No .env file found. Copy .env.example to .env and set SELLER_API_KEYS='{{\"{demo_key}\":\"{seller_id}\"}}'")
        return
    try:
        text = env_path.read_text(encoding="utf-8")
        if "SELLER_API_KEYS" not in text:
            mapping = json.dumps({demo_key: seller_id})
            try:
                with env_path.open("a", encoding="utf-8") as f:
                    f.write(f"\n# Demo seller access key\nSELLER_API_KEYS={mapping}\n")
                print(f"[i] Added default SELLER_API_KEYS to .env: key={demo_key!r} -> seller={seller_id!r}")
            except OSError:
                print(f"[i] Note: Add SELLER_API_KEYS='{mapping}' to your .env to log into the dashboard.")
    except Exception as e:
        print(f"[!] Could not inspect .env: {e}")


def seed_catalog(database: Path, seller: str) -> dict[str, dict]:
    """Create product catalog with variants and return variant lookup map."""
    existing = inventory.list_catalog(database, seller)
    lookup = {f"{v['product']}::{v.get('size')}::{v.get('color')}": v for v in existing}

    variants_to_create = [
        # Men's Panjabi
        VariantCreate(product="Premium Cotton Panjabi", size="M", color="Navy Blue", unit_price_paisa=185000, stock=8),
        VariantCreate(product="Premium Cotton Panjabi", size="L", color="Navy Blue", unit_price_paisa=185000, stock=15),
        VariantCreate(product="Premium Cotton Panjabi", size="XL", color="White", unit_price_paisa=185000, stock=3),  # low stock
        # Women's Saree
        VariantCreate(product="Tangail Cotton Saree", size=None, color="Emerald Green", unit_price_paisa=240000, stock=12),
        VariantCreate(product="Tangail Cotton Saree", size=None, color="Deep Red", unit_price_paisa=240000, stock=4),   # low stock
        # Gadgets
        VariantCreate(product="Wireless Earbuds T12", size=None, color="Matte Black", unit_price_paisa=125000, stock=25),
        VariantCreate(product="Wireless Earbuds T12", size=None, color="Glacier White", unit_price_paisa=125000, stock=18),
        # Accessories
        VariantCreate(product="Genuine Leather Wallet", size=None, color="Dark Brown", unit_price_paisa=95000, stock=10),
        VariantCreate(product="Genuine Leather Wallet", size=None, color="Tan", unit_price_paisa=95000, stock=2),      # low stock
    ]

    for var in variants_to_create:
        key = f"{var.product}::{var.size}::{var.color}"
        if key not in lookup:
            created = inventory.create_variant(database, seller, var)
            lookup[key] = created
    return lookup


def seed_orders(database: Path, seller: str, catalog: dict[str, dict]) -> list[dict]:
    """Seed orders representing each stage of the lifecycle."""
    created_orders = []
    shop_name = "Dacca Loom · ঢাকা লুম"

    # Helper to build LineItem from catalog variant
    def make_item(name: str, size: str | None, color: str | None, qty: int = 1) -> LineItem:
        key = f"{name}::{size}::{color}"
        v = catalog[key]
        return LineItem(
            product=v["product"],
            product_id=v["product_id"],
            variant_id=v["variant_id"],
            size=v["size"],
            color=v["color"],
            quantity=qty,
            unit_price_paisa=v["unit_price_paisa"],
        )

    # 1. DELIVERED ORDER (Completed cycle with courier history)
    d1 = Draft(
        shop_name=shop_name,
        customer_name="Tanvir Ahmed",
        phone="01711000001",
        address="House 42, Road 11, Sector 4, Uttara, Dhaka",
        delivery_charge_paisa=6000,
        items=[make_item("Premium Cotton Panjabi", "M", "Navy Blue", 1)],
    )
    rec1 = commerce.create_draft(database, seller, d1)
    link1 = commerce.create_link(database, seller, rec1["reference"], hours=24)
    token1 = link1["checkout_path"].split("/")[-1]
    commerce.confirm_checkout(
        database,
        token1,
        BuyerConfirmation(
            version=rec1["version"],
            customer_name="Tanvir Ahmed",
            phone="01711000001",
            address="House 42, Road 11, Sector 4, Uttara, Dhaka",
        ),
    )
    commerce.change_status(database, seller, rec1["reference"], "packed")
    commerce.change_status(database, seller, rec1["reference"], "shipped")
    commerce.update_shipment(
        database,
        seller,
        rec1["reference"],
        Shipment(courier_name="Pathao Courier", tracking_reference="PTH-DH-883921"),
    )
    commerce.change_status(database, seller, rec1["reference"], "delivered")
    created_orders.append({"status": "delivered", "ref": rec1["reference"], "customer": "Tanvir Ahmed"})

    # 2. SHIPPED ORDER (Active in transit with Steadfast courier tracking)
    d2 = Draft(
        shop_name=shop_name,
        customer_name="Nusrat Jahan",
        phone="01812000002",
        address="Flat 3B, Concord Tower, GEC Circle, Chattogram",
        delivery_charge_paisa=12000,
        items=[make_item("Tangail Cotton Saree", None, "Emerald Green", 1)],
    )
    rec2 = commerce.create_draft(database, seller, d2)
    link2 = commerce.create_link(database, seller, rec2["reference"], hours=24)
    token2 = link2["checkout_path"].split("/")[-1]
    commerce.confirm_checkout(
        database,
        token2,
        BuyerConfirmation(
            version=rec2["version"],
            customer_name="Nusrat Jahan",
            phone="01812000002",
            address="Flat 3B, Concord Tower, GEC Circle, Chattogram",
        ),
    )
    commerce.change_status(database, seller, rec2["reference"], "packed")
    commerce.change_status(database, seller, rec2["reference"], "shipped")
    commerce.update_shipment(
        database,
        seller,
        rec2["reference"],
        Shipment(courier_name="Steadfast Courier", tracking_reference="ST-CTG-449102"),
    )
    created_orders.append({"status": "shipped", "ref": rec2["reference"], "customer": "Nusrat Jahan"})

    # 3. PACKED ORDER (Ready for parcel pickup)
    d3 = Draft(
        shop_name=shop_name,
        customer_name="Rahim Chowdhury",
        phone="01913000003",
        address="Shop 12, Zindabazar, Sylhet",
        delivery_charge_paisa=12000,
        items=[make_item("Wireless Earbuds T12", None, "Matte Black", 2)],
    )
    rec3 = commerce.create_draft(database, seller, d3)
    link3 = commerce.create_link(database, seller, rec3["reference"], hours=24)
    token3 = link3["checkout_path"].split("/")[-1]
    commerce.confirm_checkout(
        database,
        token3,
        BuyerConfirmation(
            version=rec3["version"],
            customer_name="Rahim Chowdhury",
            phone="01913000003",
            address="Shop 12, Zindabazar, Sylhet",
        ),
    )
    commerce.change_status(database, seller, rec3["reference"], "packed")
    created_orders.append({"status": "packed", "ref": rec3["reference"], "customer": "Rahim Chowdhury"})

    # 4. CONFIRMED ORDER (Awaiting packing)
    d4 = Draft(
        shop_name=shop_name,
        customer_name="Farhana Karim",
        phone="01614000004",
        address="House 15, Road 3, Dhanmondi, Dhaka",
        delivery_charge_paisa=6000,
        items=[make_item("Genuine Leather Wallet", None, "Dark Brown", 1)],
    )
    rec4 = commerce.create_draft(database, seller, d4)
    link4 = commerce.create_link(database, seller, rec4["reference"], hours=24)
    token4 = link4["checkout_path"].split("/")[-1]
    commerce.confirm_checkout(
        database,
        token4,
        BuyerConfirmation(
            version=rec4["version"],
            customer_name="Farhana Karim",
            phone="01614000004",
            address="House 15, Road 3, Dhanmondi, Dhaka",
        ),
    )
    created_orders.append({"status": "confirmed", "ref": rec4["reference"], "customer": "Farhana Karim"})

    # 5. DRAFT WITH ACTIVE CHECKOUT LINK (Ready to test on buyer mobile link)
    d5 = Draft(
        shop_name=shop_name,
        customer_name="Sadman Sakib",
        phone="01315000005",
        address=None,
        delivery_charge_paisa=6000,
        items=[make_item("Premium Cotton Panjabi", "L", "Navy Blue", 1)],
    )
    rec5 = commerce.create_draft(database, seller, d5)
    link5 = commerce.create_link(database, seller, rec5["reference"], hours=24)
    created_orders.append({
        "status": "draft",
        "ref": rec5["reference"],
        "customer": "Sadman Sakib",
        "checkout_path": link5["buyer_path"],
    })

    # 6. EXTRACTED CHAT DRAFT (Simulates a raw chat extraction needing review)
    synthetic_extracted = Order(
        is_order=True,
        customer_name="Arif Hasan",
        phone="01516000006",
        address="Mirpur 10, Block C, Dhaka",
        product="Premium Cotton Panjabi",
        quantity=1,
        notes="Urgent delivery before Friday please",
        warnings=["Extracted draft: check product, quantity, price and missing buyer details."],
    )
    raw_draft = Draft(
        shop_name=shop_name,
        customer_name="Arif Hasan",
        phone="01516000006",
        address="Mirpur 10, Block C, Dhaka",
        delivery_charge_paisa=6000,
        items=[make_item("Premium Cotton Panjabi", "L", "Navy Blue", 1)],
    )
    # Use internal commerce record creator with chat source
    rec6 = commerce.record(raw_draft, "chat", synthetic_extracted)
    with commerce.closing(commerce.sqlite3.connect(database)) as conn, conn:
        conn.execute("INSERT INTO orders(payload, seller_id, record) VALUES (?, ?, ?)",
                     (synthetic_extracted.model_dump_json(), seller, json.dumps(rec6)))
    created_orders.append({
        "status": "draft (chat)",
        "ref": rec6["reference"],
        "customer": "Arif Hasan",
    })

    return created_orders


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Target SQLite database file")
    parser.add_argument("--seller", type=str, default=DEMO_SELLER, help="Seller ID")
    parser.add_argument("--no-reset", action="store_true", help="Keep existing data instead of wiping database")
    args = parser.parse_args()

    db_path = args.db.resolve()
    env_file = ROOT / ".env"

    ensure_seller_key_in_env(env_file, DEMO_KEY, args.seller)

    if not args.no_reset and db_path.exists():
        for ext in ("", "-wal", "-shm"):
            p = Path(str(db_path) + ext)
            if p.exists():
                p.unlink()
        print(f"[x] Reset database: {db_path.name}")

    initialize_database(db_path, legacy_owner=args.seller)
    print(f"[+] Initialized schema on {db_path.name}")

    catalog = seed_catalog(db_path, args.seller)
    print(f"[+] Loaded/Seeded {len(catalog)} catalog variants")

    existing_orders = commerce.list_records(db_path, args.seller)
    if args.no_reset and existing_orders:
        orders = existing_orders
        print(f"[i] Found {len(orders)} existing orders; preserving them.")
    else:
        orders = seed_orders(db_path, args.seller, catalog)
        print(f"[+] Seeded {len(orders)} realistic demo orders across lifecycle")

    active_checkout = next((o.get("checkout_path") for o in orders if isinstance(o, dict) and "checkout_path" in o), None)

    print("\n" + "=" * 60)
    print(" 🚀 DEMO READY!")
    print("=" * 60)
    print(f" Seller ID:   {args.seller}")
    print(f" Access Key:  {DEMO_KEY} (or check .env)")
    print(f" Dashboard:   http://127.0.0.1:8000/")
    if active_checkout:
        print(f" Checkout:    http://127.0.0.1:8000{active_checkout}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
