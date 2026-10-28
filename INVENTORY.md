# Catalog and stock management

The seller dashboard's **Products & stock** section manages products, size/color variants, default prices, available units, and active/inactive status. Reusing the exact product name groups variants under the same product. Duplicate size/color combinations are rejected. Product names and variant attributes are immutable in this version; create a new variant and deactivate the old one to change them.

## Seller workflow

1. Add a product variant with its default unit price and actual available units.
2. In an order draft, select the variant using **Stock tracking**. Product, size, and color fill automatically and become read-only. Quantity and the agreed unit price remain editable.
3. Save and share the draft. Drafts do not reserve stock.
4. Buyer confirmation, or a seller recording buyer agreement, deducts the catalog quantity in the same transaction as confirmation.
5. Cancelling a confirmed or packed order restores its deducted units once. Cancelling an unconfirmed draft restores nothing.
6. A returned order does not automatically restore stock. After inspecting **all** returned catalog items, choose **Restock inspected returned items**. This restores the original deducted quantities once. Partial restocking is not implemented.

Manual items remain available for compatibility and show **stock not tracked**. They require a separate stock check. AI extraction never guesses a catalog match; the seller explicitly selects the matching variant. A mixed order can contain both tracked and untracked items.

The catalog shows low stock at five units or fewer. Sold-out variants can still appear in a draft, but confirmation fails if the required quantity is unavailable. Ask the seller to adjust an item or quantity; the seller must save and issue a replacement checkout link if changing the order.

## What is protected

- Quantity checks aggregate repeated lines for the same variant.
- All item deductions and order confirmation share one SQLite transaction. A shortage or later write failure rolls back the entire operation.
- Confirmation retries return the existing receipt without deducting again. Cancellation and return restoration use recorded sale quantities and cannot restore twice.
- Catalog edits use an expected version. A sale, restock, or another catalog edit increments it; a stale stock adjustment fails instead of overwriting newer inventory. Refresh before reconciling stock.
- Changing a default catalog price affects future selections. Existing drafts and confirmed orders retain their agreed prices.
- An inactive variant cannot be confirmed. Stock may still be restored to an inactive variant after cancellation or inspection.
- Catalog lookup, editing, and order linking are seller-scoped. A seller cannot use another shop's variant.

The stock movement table records per-order sale and restoration quantities. Initial quantities and manual stock reconciliations are versioned in the catalog but are not a complete accounting/audit ledger. This pilot has no supplier purchases, multi-location stock, reservations, partial returns, or stock-import workflow.

## API

All endpoints require a seller bearer key or an authenticated browser session (with CSRF protection for writes).

| Endpoint | Use |
| --- | --- |
| `GET /seller/catalog` | List the seller's variants, available units, and versions. |
| `POST /seller/catalog` | Create a product/variant. |
| `PUT /seller/catalog/{variant_id}` | Reconcile stock, set a default price, and activate/deactivate with `expected_version`. |
| `POST /seller/orders/{reference}/restock` | Restore all inspected units from a returned order, once. |

Create request:

```json
{"product":"TEST_SHIRT","size":"M","color":"Blue","unit_price_paisa":10000,"stock":5}
```

Update request:

```json
{"expected_version":1,"unit_price_paisa":10000,"stock":8,"active":true}
```

Catalog-linked order lines must contain the returned `product_id`, `variant_id`, product name, size, and color, plus a positive quantity and agreed `unit_price_paisa`. Mismatched identity fields return 422; unavailable stock, inactive variants, or stale stock edits return 409. No new stock is reserved merely by creating a draft or checkout link.

Migration creates `products`, `variants`, and `stock_movements` without changing existing orders. Previously manual order lines are not automatically linked or retroactively deducted. Backup/restore includes inventory and movements, so cancelling a restored confirmed order restores its recorded stock correctly.

Verification: **202 offline tests pass**. Inventory tests cover seller isolation, concurrent purchases of the final unit, duplicate-line aggregation, rollback, retries, cancellation, inspected returns, stale reconciliation, agreed-price preservation, inactive variants, and recovery. The browser test covers catalog creation, variant selection, checkout deduction, and return restocking.
