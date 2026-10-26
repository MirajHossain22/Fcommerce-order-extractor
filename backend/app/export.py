"""Serialize validated orders as UTF-8 CSV."""

import csv
import io
import json
from collections.abc import Sequence

from app.schemas import Order


def orders_to_csv(orders: Sequence[Order]) -> str:
    """Use empty cells for nulls and JSON arrays for warnings."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(Order.model_fields))
    writer.writeheader()
    for order in orders:
        row = order.model_dump()
        row["is_order"] = "true" if order.is_order else "false"
        row["warnings"] = json.dumps(order.warnings, ensure_ascii=False)
        writer.writerow(row)
    return output.getvalue()
