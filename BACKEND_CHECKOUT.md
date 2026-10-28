# Order lifecycle and checkout API

Updated October 28, 2026. Execution steps 2–7 are implemented for local use, including the seller dashboard, browser sessions, buyer form, confirmation, receipt, and tracking with seller-entered courier details. Courier API integration remains pending. See [deployment and recovery instructions](DEPLOYMENT.md) for Step 8 preparation.

## Configure seller access

Generate a random seller key locally:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the generated key to `.env` as a JSON mapping. Replace the placeholder below; do not use it as an actual key:

```dotenv
SELLER_API_KEYS={"REPLACE_WITH_GENERATED_SECRET":"legacy"}
```

Each key maps to a seller ID. Add independent keys/IDs for additional sellers. Keys sharing an ID intentionally share access. Environment variables override `.env`; restart the app after changing keys. Empty configuration returns 503 for seller endpoints; absent/incorrect credentials return 401 when access is configured. There is no public account registration. Keep keys on the seller side and use HTTPS for any hosted deployment.

The default migration assigns old records to the reserved seller ID `legacy`. Mapping your key to `legacy` lets you access your existing data. For a programmatically configured app, `create_app(..., legacy_owner="your-seller-id")` selects a different owner only on the first migration. Restarting with a different owner never reassigns existing orders. Back up an existing SQLite file before deploying the migration. No real database was migrated during development verification; tests use temporary files.

Run the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` and sign in with your seller key. The UI offers manual drafts, optional chat extraction, multiple line items, price review, search/filtering, checkout-link creation/copying/revocation, and status updates. AI extraction still requires provider configuration; manual checkout does not.

The server exchanges the key for an eight-hour HttpOnly, SameSite=Strict session cookie. Cookies also use Secure when served over HTTPS. Browser writes require a session CSRF token; cross-origin writes are rejected. Only hashes of session tokens and associated keys are stored. Key rotation invalidates sessions on the next request after restart; sign-out deletes the active session. The UI stores neither seller keys nor buyer details in localStorage/sessionStorage. If deployed behind a proxy, configure trusted proxy handling so the application receives the correct HTTPS scheme and host.

Browser workflow: sign in → create/review draft → save → create checkout link → copy into Messenger → buyer enters delivery details → confirms → receives private tracking link. The buyer sees the shop name, items, variants, delivery charge, and COD total before confirming. Buyer labels include Bangla and English. Catalog-linked stock is checked at confirmation; manual items need seller stock checks; seller-entered tracking is not a live courier feed.

Loopback links work only on the computer running the app. Sharing with actual buyers requires a reachable deployment and HTTPS; this batch does not publish a pilot.

## Endpoints

Use `Authorization: Bearer <seller-key>` on every seller endpoint, including `POST /extract`, `POST /extract/batch`, `GET /orders`, and `GET /orders/export.csv`, or use the dashboard session and its CSRF header for writes. These retain their original response shapes but restrict records to the authenticated seller. They list/export original chat extraction results, not edited commercial order snapshots; manually created drafts appear only in the new seller API.

| Method and path | Purpose |
| --- | --- |
| `POST /seller/orders` | Create a manual draft without an AI provider. |
| `GET /seller/orders` | List the seller's manual and extracted drafts/orders, newest first. |
| `GET /seller/orders/{reference}` | Read full details and status history. |
| `PUT /seller/orders/{reference}` | Replace editable draft details; omitted optional fields reset to defaults. |
| `POST /seller/orders/{reference}/status` | Apply a permitted status transition. |
| `PUT /seller/orders/{reference}/shipment` | Save courier name and tracking reference for a confirmed, non-cancelled order. |
| `POST /seller/orders/{reference}/checkout-links` | Create a link with an expiry; revoke previously issued links. |
| `DELETE /seller/orders/{reference}/checkout-links` | Revoke all links for that order. |
| `GET /checkout/{token}` | Public token-protected JSON checkout summary; no seller key required. |
| `POST /checkout/{token}/confirm` | Atomically confirm with reviewed version, name, phone, and address. |
| `GET /checkout/{token}/receipt` | Recover a confirmed receipt after refreshing or reopening the link. |
| `GET /api/tracking/{token}` | Private buyer status/history and item/price summary. |
| `POST /session` | Exchange a seller key for a browser session; requires `X-Requested-With: checkout-app`. |
| `GET /session` | Restore the active seller session and its CSRF token. |
| `DELETE /session` | Sign out and revoke the current session. |

The UI routes are `/` (seller), `/buy/{token}` (buyer checkout/receipt), and `/track/{token}` (tracking). Static assets are served by FastAPI; no Node build or frontend dependency installation is needed. Courier requests use `{"courier_name":"TEST_COURIER","tracking_reference":"TEST_PARCEL_001"}`. Repeating unchanged details does not duplicate the history event. Updating courier details does not book a shipment, change status, or change prices. Buyer tracking displays the details as text, not as an unverified external URL.

Unknown orders and orders belonging to another seller both return 404. Invalid request fields/types return 422. Lifecycle conflicts return 409. Unknown checkout tokens return 404; expired or revoked sessions return 410. Responses disable caching and referrer forwarding.

## Try a complete backend workflow

In a PowerShell session, assign your generated key to `$sellerKey` locally, then run:

```powershell
$headers = @{ Authorization = "Bearer $sellerKey" }
$base = "http://127.0.0.1:8000"
$body = @{
    customer_name = "TEST_BUYER"
    phone = "01800000001"
    address = "TEST_ADDRESS"
    items = @(@{
        product = "TEST_SHIRT"
        size = "M"
        color = "Blue"
        quantity = 2
        unit_price_paisa = 35050
    })
    delivery_charge_paisa = 6000
} | ConvertTo-Json -Depth 5
$order = Invoke-RestMethod "$base/seller/orders" -Method Post -Headers $headers -ContentType "application/json" -Body $body
$reference = $order.reference
$link = Invoke-RestMethod "$base/seller/orders/$reference/checkout-links" -Method Post -Headers $headers -ContentType "application/json" -Body '{"expires_in_hours":24}'
Invoke-RestMethod "$base$($link.checkout_path)"
```

Money uses integer paisa: 35050 means BDT 350.50. The server calculates the total: two items plus delivery above equals 76100 paisa (BDT 761.00). Clients cannot supply a total. Product/variant IDs link items to the seller catalog for stock validation. Unlinked manual items are not tracked; see INVENTORY.md.

New links are usable for 1–168 hours, defaulting to 24. Only token hashes are stored. The API returns `checkout_path` for the JSON API and `buyer_path` for the buyer page. The seller UI combines `buyer_path` with its current origin. A link exposes item and price information, but no buyer name, phone, address, or raw extraction. Draft edits increment the version and revoke prior links; sellers must issue and share a replacement.

To confirm through the API, POST a body such as `{"version":1,"customer_name":"TEST_BUYER","phone":"01800000001","address":"TEST_ADDRESS"}` to `{checkout_path}/confirm`. The server validates the current version, session expiry/revocation, buyer details, stored items and calculated total. Prices and items cannot be overridden in this request. Item corrections require the seller to edit the draft and issue a new link.

Confirmation updates the existing draft in one transaction and records one confirmation event. Concurrent requests and retries return the same receipt; changed retry details never replace the confirmed details. A confirmed link can recover its receipt even after its original checkout expiry. Receipts and tracking links contain item/price information, not buyer contact data. The tracking token is separate from the checkout token and grants no seller access. Tracking links currently remain valid indefinitely; token revocation/retention policy is future pilot-hardening work.

## Lifecycle and storage

Extraction creates an unconfirmed draft while preserving its original payload. Product and quantity remain extraction hints in `extracted_order` until a seller explicitly supplies reviewed line items, prices, and variants. Missing/blank buyer details remain incomplete. No price or purchase confirmation is inferred by AI.

Seller status requests use a body such as `{"status":"confirmed"}`. A seller must actually have the buyer's agreement before manually confirming; the dashboard asks them to attest to it. The buyer-confirmation flow is separate and records the buyer's confirmation. Manual seller confirmation does not issue a buyer receipt or tracking token; share the buyer checkout link first when using the buyer flow.

Allowed transitions:

- Draft → confirmed or cancelled.
- Confirmed → packed or cancelled.
- Packed → shipped or cancelled.
- Shipped → delivered or returned.
- Delivered → returned.
- Cancelled and returned are terminal.

Confirmation requires reviewed items, name, valid phone, and address. Confirmed details cannot be edited through the draft API. Status changes preserve the agreed price snapshot, append history, and revoke unconfirmed checkout sessions. State changes use SQLite transactions. Creating manual drafts and calling extraction repeatedly can still produce duplicate drafts; confirmation of a given checkout session is retry-safe.

Migration adds seller ownership and a commercial record to the existing `orders` table and creates `checkout_sessions`, `tracking_links`, and `seller_sessions`. Existing checkout tables gain a confirmation marker without losing prior sessions. Migration preserves legacy payloads and internal row IDs, assigns stable references, and can be run repeatedly without recreating references. Local backup/restore checks are implemented. Inventory is implemented for linked catalog items. Host recovery drills, rate limiting, courier API integration, and deployment remain future work.

## Verification

Run `.\.venv\Scripts\python.exe -m pytest -q` from the repository root. Current result: **218 passed**, with one upstream Starlette test-client deprecation warning. Coverage includes migration preservation, seller isolation, session expiry/revocation/CSRF, price validation, eight concurrent confirmation attempts, rollback on failed tracking writes, receipt recovery, courier details, backup/restore, Render deployment configuration, and the regex baseline. All checks are offline; live AI accuracy remains unverified.

Optional real-browser verification: `node backend/tests/browser_smoke.mjs`. It uses Node's built-in browser-protocol client, local Chrome, and the Python virtual environment; no npm packages are required. Defaults target Windows; `CHROME_PATH` and `PYTHON_PATH` may override the executable locations. It creates synthetic data and screenshots under `.pytest_cache`, starts a temporary local server, and closes its server/browser afterward. The check passed on October 28, 2026. It exercises login, catalog selection, a manual draft, totals, sharing, a 390px buyer screen, confirmation, stock deduction, receipt reload, seller status and courier updates, return restocking, session restoration, and logout. It does not call the AI provider or touch the real order database.
