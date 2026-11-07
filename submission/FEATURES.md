# Feature Map — F-Commerce Order Extractor (Order Desk)

**Project:** F-Commerce Order Extractor ("Order Desk")  
**Live URL:** [https://fcommerce-order-extractor.onrender.com/](https://fcommerce-order-extractor.onrender.com/)  
**Role:** Frontend Engineer Intern Submission — Phase 02 (Credosis)  
**Candidate:** Miraj Hossain  

---

## Overview

In Bangladesh, over 80% of informal social commerce (F-commerce) happens inside conversational Facebook and Messenger threads. This creates three critical operational breakdowns:
1. **Misplaced and Incomplete Orders:** Customer delivery details (vague addresses, missing phone numbers) get buried in long chat histories.
2. **Stock Tracking Errors & Overselling:** Sellers take orders for items already sold out, causing embarrassing cancellations and damaged customer trust.
3. **Delivery Status Anxiety:** Customers repeatedly ping sellers ("Bhai parcel kothay?") because there is no automated tracking channel.

The **Order Desk** bridges conversational selling and structured fulfillment. It allows sellers to convert chat conversations into verified orders, generate a **mobile-first private checkout link** that works inside Messenger (zero app install), and track fulfillment through a responsive dashboard.

---

## 1. Core Feature (Primary Submission Focus)

### Mobile-First Private Checkout Link & Customer Confirmation Flow

| Attribute | Details |
|---|---|
| **Problem Solved** | Eliminates misplaced orders, missing addresses, and arguments over agreed items/prices without forcing the customer to leave Messenger or install an app. |
| **User Value** | The buyer receives a secure, branded link in their Messenger chat. In under 30 seconds, they review the exact items and Cash on Delivery (COD) total, enter their delivery details, and receive an instant digital receipt with a private tracking page. |
| **Backend Implementation** | - `backend/app/commerce.py`: `create_link()`, `checkout_summary()`, `confirm_checkout()`, `buyer_receipt()`, `tracking_token()`.<br/>- `backend/app/main.py`: `POST /seller/orders/{ref}/checkout-links`, `GET /checkout/{token}`, `POST /checkout/{token}/confirm`.<br/>- `backend/app/normalize.py`: `normalize_phone()` validating BD mobile patterns (`^01[3-9]\d{8}$`). |
| **Frontend Implementation** | - `frontend/buyer.html`: Lightweight semantic HTML view loaded on `/buy/{token}` and `/track/{token}`.<br/>- `frontend/buyer.js`: Zero-dependency ES module handling summary rendering, form validation, submit states, and view switching.<br/>- `frontend/seller.js`: Link generation trigger, countdown expiration display, and one-click clipboard copying. |

#### How It Works Under the Hood
1. **Cryptographic Token Isolation:** When the seller clicks "Create checkout link", the server generates a 32-byte URL-safe cryptographic token. Only its SHA-256 hash is stored in the database (`checkout_sessions`).
2. **Version Locking (Anti-Tamper):** If the seller edits items or prices in the dashboard, the draft's `version` increments, automatically revoking older checkout links so buyers never pay for outdated drafts.
3. **Atomic Confirmation Transaction:** When the buyer taps "Confirm order", SQLite executes an immediate transaction:
   - Validates draft status and token expiration.
   - Atomically decrements catalog inventory for tracked variants.
   - Transitions order status from `draft` to `confirmed`.
   - Revokes the checkout token (`revoked = 1`) and marks it confirmed.
   - Generates a domain-separated tracking token: `sha256("tracking-v1:" + token)`.
4. **Idempotent Retry Safety:** If a buyer experiences a flaky mobile connection and re-submits, the endpoint safely returns the existing receipt without double-deducting stock or creating duplicate orders.

#### How to Demo in the UI
1. In the seller dashboard, select an order in `draft` status (e.g. **Arif Hasan**).
2. Review items and click **"Create checkout link"**.
3. Click **"Copy"** on the generated link and open it in a separate browser tab (or mobile responsive preview) at `/buy/<token>`.
4. Observe the clean mobile summary card: bilingual Bangla/English labels, line items, delivery fee, and COD total in BDT.
5. Fill in the delivery form:
   - Name: `Arif Hasan`
   - Phone: `01712345678`
   - Address: `House 14, Road 3, Sector 9, Uttara, Dhaka`
6. Click **"Confirm order · অর্ডার নিশ্চিত করুন"**.
7. Observe instant confirmation: shows a green checkmark, confirmed summary, and a button to **"Follow order updates"** (`/track/<token>`).

---

## 2. Supporting Features

### Supporting Feature 1: Real-Time Catalog Stock Tracking & Atomic Inventory Deduction

| Attribute | Details |
|---|---|
| **Problem Solved** | Prevents overselling and stock errors. Sellers often sell products in chat without realizing the specific size or color variant is already out of stock. |
| **User Value** | Sellers manage product variants (size/color), unit prices, and live stock counts. Drafts link directly to catalog variants, stock is automatically decremented upon buyer confirmation, and low-stock alerts notify sellers when $\le 5$ units remain. |
| **Key Code Files** | - `backend/app/inventory.py`: `create_variant()`, `update_variant()`, `validate_items()`, `consume()`, `restore()`.<br/>- `backend/app/commerce.py`: `restock_return()`.<br/>- `frontend/seller.html` & `frontend/seller.js`: Catalog accordion, line item variant dropdown (`populatePicker`), and inline variant editor. |

#### How It Works Under the Hood
- **Optimistic Concurrency Control:** Every variant row has a `version` integer. When a seller edits stock or pricing, the client sends `expected_version`. If a concurrent checkout occurred, the update is rejected with `409 Conflict`, preventing accidental stock overwrites.
- **Atomic SQL Decrement:** Stock is deducted in SQLite with `UPDATE variants SET stock=stock-?, version=version+1 WHERE id=? AND stock>=? AND active=1`. If stock is insufficient, the entire order confirmation transaction rolls back.
- **Idempotent Return Restocking:** If an order is returned, the seller can inspect the parcel and click "Restock inspected returned items". The system checks `stock_movements` and restores stock exactly once, preventing double-restocking.

#### How to Demo in the UI
1. Expand the **"Products & inventory stock"** accordion on the seller dashboard.
2. Note the stock counts and low-stock indicator on items like **Premium Cotton Panjabi · XL · White (3 available · Low stock)**.
3. In a draft, add an item and select a variant from the **"Stock tracking"** dropdown. Observe product name, size, color, and unit price lock into place automatically.
4. Confirm the order $\rightarrow$ refresh catalog and show that available units decreased by the exact ordered amount.
5. Filter by `returned` order, click **"Restock inspected returned items"** $\rightarrow$ show that stock is restored and marked in the audit history.

---

### Supporting Feature 2: Structured Order Desk & Progression State Machine

| Attribute | Details |
|---|---|
| **Problem Solved** | Eliminates order chaos and customer delivery anxiety. Gives the seller a single dashboard to track orders through fulfillment, and gives buyers a self-serve tracking link. |
| **User Value** | Sellers see at-a-glance order statistics, instant search by customer name or product, and a strict status progression workflow. Sellers can add courier details (Steadfast, Pathao) that immediately appear on the buyer's private tracking link. |
| **Key Code Files** | - `backend/app/commerce.py`: `TRANSITIONS` state machine dictionary, `change_status()`, `update_shipment()`, `track_order()`.<br/>- `backend/app/main.py`: `/seller/orders`, `/seller/orders/{ref}/status`, `/seller/orders/{ref}/shipment`, `/api/tracking/{token}`.<br/>- `frontend/seller.html` & `frontend/seller.js`: Metrics bar, order card rendering, status badges, history timeline, and search/filter logic. |

#### How It Works Under the Hood
- **Enforced State Machine:** Orders cannot arbitrarily jump statuses. Transitions strictly follow:
  $$\text{draft} \rightarrow \text{confirmed} \rightarrow \text{packed} \rightarrow \text{shipped} \rightarrow \text{delivered}$$
  Cancellations are allowed from `draft`, `confirmed`, or `packed`; returns are allowed from `shipped` or `delivered`.
- **Courier Delivery Integration:** When marked `shipped`, the seller enters courier name and tracking code. This data updates the order record and immediately renders on the buyer's private `/track/{token}` timeline without needing an external app.
- **Integer Paisa Currency Calculation:** All money calculations are computed in integer paisa ($\text{total} = \sum (\text{qty} \times \text{unit\_price}) + \text{delivery}$) to completely eliminate IEEE-754 floating-point rounding errors.

#### How to Demo in the UI
1. Point out the top stat counters: **Total orders (6)**, **Need review (2)**, **In progress (3)**, **Delivered (1)**.
2. Type in the search box (e.g. `"Panjabi"` or `"Arif"`) and select a status filter to demonstrate real-time client-side filtering.
3. Select an order in `confirmed` status $\rightarrow$ choose next status **"Packed"** $\rightarrow$ click **"Update status"**.
4. Advance to **"Shipped"** $\rightarrow$ fill in Courier details:
   - Courier: `Steadfast Courier`
   - Consignment / Tracking Ref: `ST-982341`
5. Click **"Save courier info"** $\rightarrow$ open the buyer's tracking link in another tab $\rightarrow$ show the live tracking timeline and courier delivery card.

---

### Supporting Feature 3: AI Chat Order Extractor with Substring Verification Guard

| Attribute | Details |
|---|---|
| **Problem Solved** | Eliminates manual copy-pasting fatigue and human data-entry errors when customers send long, informal chat messages. |
| **User Value** | Sellers paste raw Facebook/Messenger chat messages (in Bangla, Banglish, or English). The AI extractor pulls out customer name, phone number, delivery address, product, and quantity into an editable draft in seconds. |
| **Key Code Files** | - `backend/app/extractor.py`: `SYSTEM_PROMPT`, `validate_extraction()`, Gemini 1.5/2.0 API client.<br/>- `backend/app/normalize.py`: `normalize_digits()` (Bangla numerals conversion), `normalize_phone()`.<br/>- `frontend/seller.js`: `#extract` click handler, loading spinner, and error banner handling. |

#### How It Works Under the Hood
- **Substring Hallucination Guard:** LLMs are notorious for hallucinating missing details. To guarantee zero invented data, Python application logic verifies that every extracted string (`customer_name`, `phone`, `address`, `product`, `notes`) is a **literal substring** of the original message after normalizing Bangla numerals. If a field fails this check, it is discarded with a warning.
- **Bangla Digit & Phone Normalization:** Converts Bengali numerals (`০১২৩৪৫৬৭৮৯` $\rightarrow$ `0123456789`), removes whitespace/dashes, handles `+880` / `880` prefixes, and validates the 11-digit Bangladeshi mobile format.
- **Graceful Offline Fallback:** If the LLM provider hits rate limits or is unconfigured, the app falls back to a deterministic regex baseline, and manual draft creation continues to work 100% without dependencies.

#### How to Demo in the UI
1. Click **"+ New order draft"** on the seller dashboard.
2. In the "Extract draft from chat message" box, paste a realistic sample chat:
   ```text
   Assalamu alaikum bhai, ami 1 ta Navy Blue Panjabi nibo, L size.
   Amar address: House 12, Road 4, Sector 10, Uttara, Dhaka.
   Phone: 01712345678. Urgent delivery lagbe please.
   ```
3. Click **"Extract draft from chat"**.
4. Show that the draft is created with:
   - Customer name, phone, and address populated.
   - Product hint set to "Navy Blue Panjabi".
   - Special notes captured ("Urgent delivery lagbe please").
   - Warning banner: *"Extracted draft: check product, quantity, price and missing buyer details."*

---

## 3. Extra Features (Brief Mention in Docs / Interview)

1. **Reviewer Demo Key & Auto-Fill Gateway:** Built specifically for Credosis reviewers. The login screen displays `demo-seller-key` with a one-click auto-fill button that bypasses friction.
2. **Formula-Injection Safe CSV Export:** `GET /orders/export.csv` exports seller orders with a UTF-8 BOM (so Bangla text opens properly in Microsoft Excel) and sanitizes dangerous formula characters (`=`, `+`, `-`, `@`).
3. **Session Security & CSRF:** 8-hour HttpOnly SameSite=Strict cookies with custom SHA-256 derived CSRF tokens (`seller-csrf-v1:`) and origin validation.
4. **SQLite Snapshot Backups:** `backend/app/backup.py` creates clean point-in-time database snapshots verifying SQLite Write-Ahead Logging (WAL) checkpoints before copy.
5. **Offline Evaluation Harness:** `eval/run_eval.py` tests extraction accuracy against a 50-message synthetic dataset comparing Gemini to the regex baseline across field-level and order-level metrics.

