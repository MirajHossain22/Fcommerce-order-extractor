# Step-by-step execution plan

Status reviewed: October 28, 2026 (Asia/Dhaka).

## Product idea

Help small Facebook shops in Bangladesh turn chat conversations into clear, trackable orders. Sellers currently risk losing order details and mixing up stock, sizes, and colors. Buyers keep screenshots, repeatedly ask for updates, and retype their address in different chats.

The proposed flow is: seller creates or extracts an order draft, checks it, and shares a mobile checkout link in Messenger. The buyer checks the product, size, color, quantity, delivery details, and cash-on-delivery total, then confirms. Both sides receive an order reference, and the buyer can check progress through a tracking link.

“Two taps” is a usability target for a returning buyer whose details are already available. A first-time buyer still needs to enter and review their details. Tracking makes delivery progress visible; it cannot itself guarantee faster courier delivery.

## Current implementation status

The basic portfolio build is complete for local use, with **241 passing offline tests**. The seller dashboard supports browser sessions, extraction review, manual drafts, search/filtering, and status actions. Sellers can create and copy checkout links. Buyers can review items, enter delivery details, confirm once, recover a receipt, and open a private tracking page. See [setup and examples](BACKEND_CHECKOUT.md).

Step 7 is complete locally: buyers see seller-entered status, history, courier name, and parcel reference. Step 8 now has verified backup/restore tooling, an explicit persistent-storage launcher, host checks, a health endpoint, a locally verified Docker image, and an optional paid Render Blueprint. The image passed health and named-volume restart persistence checks with synthetic data. Desktop and 390px mobile flows were checked in headless Chrome. The app has not been deployed; hosting is paused while local Docker is evaluated.

Step 10 is also implemented locally: seller catalog, variant selection, atomic stock deductions, cancellation restoration, explicit return restocking, and low-stock displays. Manual items remain untracked. See [inventory behavior and limits](INVENTORY.md). Step 9 address reuse remains a separate pending feature.

## What is done so far

| Existing phase | Status | Evidence and limits |
| --- | --- | --- |
| 1. Order schema, configuration, normalization | Implemented | `backend/app/schemas.py`, `config.py`, and `normalize.py`; missing information remains null, and Bangla digits and phone formats are normalized. |
| 2. AI extraction and CLI | Implemented; live accuracy unverified | `backend/app/extractor.py`; Gemini integration, source checks, validation, and mocked tests exist. |
| 3. API, storage, CSV | Implemented for local use | `backend/app/main.py` and `export.py`; single/batch extraction, SQLite persistence, order listing, and CSV download exist. |
| 4. Evaluation tools | Implemented; successful live evaluation remains | 50-message dataset, scoring, and failure reports exist. The recorded live run had 50 extraction errors and no usable predictions. Its 0% score is not measured model prediction accuracy. |
| Local regex baseline | Implemented and scored | `eval/baseline.py` scored 46.00% exact-order accuracy (23/50) and 83.43% mean field accuracy with zero extraction errors; see `eval/results-baseline.md`. |
| Automated verification | Passing | 241 offline tests passed without warnings on October 28, 2026. Adversarial checks cover bounded inputs, malformed authentication, tenant isolation, traversal attempts, CSV formulas, stored XSS, concurrency, and retry behavior. Mocked tests do not establish live AI quality. |
| Frontend | Implemented locally | Seller dashboard, buyer checkout/receipt, and private status tracking in `frontend/`; responsive flow verified in Chrome. |
| Order lifecycle, seller access, checkout sessions | Backend implemented | `commerce.py`, `seller_auth.py`, and API routes; see current batch above. |

The API saves extractions as unconfirmed drafts with stable references and history, including incomplete records. Repeated extraction requests can still create duplicate drafts. Seller keys and browser sessions protect reads, edits, and exports. Buyer confirmation is atomic and retry-safe. Address reuse, courier API integration, pilot deployment, and live AI quality verification remain pending. Stock automation applies only to explicitly linked catalog variants.

## Execution order

Steps 1–8 build the first usable checkout pilot. Step 9 adds returning-buyer convenience; steps 10–11 extend operations. AI evaluation can proceed alongside checkout development because manually created checkout drafts must work without an AI provider.

### Step 1 — Establish the baseline and finish evaluation follow-up

- [x] Inspect the current implementation and run the offline suite: 241 passed after deployment and adversarial hardening checks were added.
- [x] Review the existing regex baseline work and produce a separate baseline report.
- [ ] When live evaluation resumes, check provider availability and quota, then run a small synthetic sample before the full dataset.
- [ ] Preserve separate reports and distinguish request failures from incorrect predictions.

Completion check: baseline results are recorded, and AI quality is either measured with usable predictions or explicitly marked unverified. Do not block manual checkout on provider availability.

### Step 2 — Add an order lifecycle and migrate existing storage

- [x] Keep the extraction result separate from a confirmed purchase; preserve the current extraction contract or document any API migration.
- [x] Add seller ownership, stable order references, timestamps, source (`chat` or `checkout`), and status history.
- [x] Add line items with product/variant references, explicit size and color where applicable, quantity, and a price snapshot in BDT.
- [x] Store delivery charge, server-calculated total, and payment method (`cash_on_delivery` initially).
- [x] Define allowed transitions: draft → confirmed → packed → shipped → delivered, with cancellation rules and a separate returned outcome after shipment.
- [x] Migrate existing records without data loss; treat old extracted rows as unconfirmed drafts requiring review.

Completion check: old records remain readable, drafts can be edited, invalid status changes fail, and a confirmed order preserves the agreed items and total.

### Step 3 — Add seller access and order review

- [x] Add seller API-key authentication and enforce ownership on every seller read/write/export endpoint.
- [x] Add browser login/session handling for the seller dashboard.
- [x] Build a mobile-friendly seller screen to paste chat text, review extraction warnings, edit fields, or create a draft manually.
- [x] Show missing information clearly; never infer a buyer's agreement from AI classification.
- [x] Add order lists, search, filters, and order details with permitted status actions.

Completion check: a seller can prepare a draft without AI, and one seller cannot access another seller's orders or exports.

### Step 4 — Generate a shareable checkout link

- [x] Create a checkout session for a reviewed draft, using an unguessable token, expiry, and revocation support.
- [x] Add a copy-link action so the seller can paste the URL into Messenger manually.
- [x] Keep customer information out of the URL and expose only the information needed for checkout.
- [x] Define what happens if a seller edits a draft after sharing: invalidate or version the old session and require review of the latest total.

Completion check passed locally: tokens resolve the correct draft, the buyer form works at phone width, and expired/revoked/altered tokens fail safely. Automatic Messenger messaging is a later integration.

### Step 5 — Build the buyer's mobile checkout form

- [x] Show the shop, items, size/color, quantities, prices, delivery charge, and COD total.
- [x] Collect name, normalized phone, and delivery address; allow corrections before confirmation.
- [x] Support readable Bangla and English labels, clear errors, and small phone screens.
- [x] Add an explicit final confirmation action with loading and retry behavior.
- [x] Validate quantities, variant fields, required fields, and totals on the server. Buyers cannot change agreed items/prices; catalog availability validation belongs to Step 10.

Completion check: a first-time buyer can complete a checkout from a shared link and understands exactly what will arrive and what they will pay.

### Step 6 — Confirm once and issue a receipt

- [x] Convert the draft into a confirmed order in one database transaction.
- [x] Make repeated submissions and network retries return the same order rather than create duplicates.
- [x] Prevent an old checkout link from silently changing an already confirmed order.
- [x] Show an order reference, item summary, COD amount, and a private tracking link.

Completion check: double taps and retries create exactly one order; buyer and seller see the same confirmed details after restart.

### Step 7 — Add buyer tracking and seller status updates

- [x] Provide a private tracking page with current status and timestamped status history.
- [x] Let the seller record packing, shipped status, delivery, cancellation, and return as appropriate.
- [x] Add courier name and courier tracking reference entry/display.
- [x] Keep tracking tokens separate from seller access; expose only necessary customer information.
- [x] Label seller-entered updates accurately. Live courier tracking remains a later feature.

Completion check: a seller's status update appears on the buyer's tracking page, and another buyer cannot enumerate orders by changing an order number.

### Step 8 — Verify and deploy a small pilot

- [x] Test the local flow with synthetic data: draft → shared link → buyer details → confirmation → tracking, including receipt reload.
- [x] Cover duplicate submission, expired links, missing details, unauthorized access, and changed prices.
- [x] Verify local mobile use, persistence, database migration, and backup/restore with synthetic data.
- [x] Prepare persistent-storage configuration, startup host/secret checks, a health endpoint, and a container starter.
- [x] Add an optional Render Blueprint for a paid single-instance SQLite pilot in Singapore; the user declined payment for now.
- [x] Build and verify the container, health endpoint, and named-volume persistence on a running Docker engine.
- [ ] Create the Render service, then verify its generated HTTPS origin, proxy settings, persistent volume, backups, and secrets before using real orders.
- [ ] Run a small seller/buyer pilot and record completion time, checkout abandonment, corrected details, duplicate orders, and status enquiries.

Completion check: the deployed pilot supports the full manual checkout flow reliably. Describe AI extraction as experimental until successful live evaluation supports stronger claims.

### Step 9 — Reuse delivery details with buyer control

- [ ] Add an opt-in “save my delivery details” feature with a defined storage and authentication design.
- [ ] Let returning buyers review, edit, and delete saved details; handle shared devices and sign-out.
- [ ] Never reveal saved addresses merely because someone knows a phone number.
- [ ] Measure the returning-buyer path before advertising “two taps.”

Completion check: an authorized returning buyer can reuse details without retyping, while another user cannot retrieve those details. Reuse across shops requires a shared buyer account design; browser autofill alone does not guarantee it.

### Step 10 — Add product variants and reliable stock management

- [x] Create a seller catalog with products, size/color variants, prices, and available quantities.
- [x] Link draft line items to actual catalog variants; require seller review when extracted product text is ambiguous.
- [x] Check and deduct stock atomically at confirmation; drafts do not reserve stock initially.
- [x] Restore stock exactly once for eligible cancellations; returned items require a restock decision.
- [x] Show out-of-stock errors and low-stock information.

Completion check: two simultaneous buyers cannot both buy the last unit, retries do not deduct twice, and cancellation does not restore stock twice. Catalog-linked items are tracked automatically; manual items still require seller stock checks.

### Step 11 — Add courier and Messenger automation

- [ ] Choose integrations based on pilot needs and verify their current API access requirements during implementation.
- [ ] Add courier booking and delivery updates with authenticated callbacks, retry handling, and duplicate-event protection.
- [ ] Keep delivery status and COD collection/settlement status separate.
- [ ] Add automatic Messenger handling only after access, permissions, and message behavior are established.

Completion check: external failures are visible, retries do not create duplicate shipments/messages, and manual order handling remains available.

## Next implementation task

The local MVP is finished. The next meaningful milestone is external validation: restore Gemini access and record a usable live evaluation, then choose a host with persistent storage and run a small synthetic pilot before accepting real data. Saved buyer accounts, courier integration, and Messenger automation are later product expansions, not blockers for the basic portfolio build.
