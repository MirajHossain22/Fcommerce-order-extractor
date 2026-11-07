"""Self-healing demo seed data for review and testing."""

import json
from pathlib import Path
import sqlite3
from contextlib import closing

from app import commerce, inventory
from app.commerce import Draft, LineItem, Shipment, BuyerConfirmation
from app.inventory import VariantCreate
from app.schemas import Order


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

    # 1. DELIVERED ORDER
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

    # 2. SHIPPED ORDER
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

    # 3. PACKED ORDER
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

    # 4. CONFIRMED ORDER
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

    # 5. DRAFT WITH ACTIVE CHECKOUT LINK
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

    # 6. EXTRACTED CHAT DRAFT
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
    rec6 = commerce.record(raw_draft, "chat", synthetic_extracted)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("INSERT INTO orders(payload, seller_id, record) VALUES (?, ?, ?)",
                     (synthetic_extracted.model_dump_json(), seller, json.dumps(rec6)))
    created_orders.append({
        "status": "draft (chat)",
        "ref": rec6["reference"],
        "customer": "Arif Hasan",
    })

    return created_orders


def auto_seed_if_empty(database: Path, seller: str = "local-shop") -> bool:
    """If database has 0 orders, populate demo store so reviewers never see empty states."""
    try:
        with closing(sqlite3.connect(database)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            count = row[0] if row else 0
        if count == 0:
            catalog = seed_catalog(database, seller)
            seed_orders(database, seller, catalog)
            return True
    except Exception:
        pass
    return False
