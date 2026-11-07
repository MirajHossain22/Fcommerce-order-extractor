# Code Architecture Explainer & Technical Interview Prep

**Project:** F-Commerce Order Extractor ("Order Desk")  
**Candidate:** Miraj Hossain  
**Role:** Frontend Engineer Intern at Credosis  

---

## Part 1: Deep Dive into Key Files & Functions

### 1. `frontend/buyer.js` — Mobile-First Checkout Controller
- **What it does:** Powers the customer-facing checkout page (`/buy/{token}`) and tracking view (`/track/{token}`). It fetches order details, renders item summaries, validates delivery inputs, handles form submission with optimistic loading states, and switches to the confirmed receipt/tracking view.
- **Why it’s written this way:** 
  - Uses native ES modules with zero external libraries or bundle build steps.
  - Keeps the initial payload under 15 KB so customers in Bangladesh on 3G connections experience instant load times inside Facebook Messenger's embedded webview.
  - Shares the same HTML file (`buyer.html`) for both checkout and tracking, inspecting `location.pathname.startsWith('/track/')` to dynamically toggle between the checkout form and the progress timeline.
- **Data Flow:**
  1. `load()` calls `GET /checkout/{token}` (or `GET /api/tracking/{token}`).
  2. Data flows into `showSummary()`, which populates the DOM and formats prices via `money()`.
  3. On submit, form data (`customer_name`, `phone`, `address`, and `version`) is POSTed to `/checkout/{token}/confirm`.
  4. On success, `showReceipt()` hides the input panel, displays the success checkmark, and wires up the tracking URL.

---

### 2. `frontend/seller.js` — Seller Dashboard State & DOM Engine
- **What it does:** Coordinates the seller workspace. Manages client-side order state (`orders = []`), catalog items (`catalog = []`), active selection (`selected`), form dirty tracking (`dirty`), line items, search/filtering, and status transitions.
- **Why it’s written this way:**
  - Encapsulates network operations inside `run(action)` to automatically manage loading states, disable buttons, and prevent double-clicks during async requests.
  - The `api()` wrapper automatically attaches the session CSRF token (`X-CSRF-Token`) to all mutating requests and redirects to login if the session returns 401.
  - Includes a `canLeave()` guard before switching orders or extracting messages, warning the seller if they have unsaved form changes.
- **Data Flow:**
  - `refresh()` loads `/seller/orders` and `/seller/catalog` concurrently via `Promise.all()`.
  - `renderOrders()` filters the array in-memory based on search text and status filters, rendering DOM elements using the `node()` builder without innerHTML string concatenation vulnerabilities.
  - `selectOrder(order)` sets up the editor drawer, populating line items, history timelines, and restricted status choices based on the state machine.

---

### 3. `frontend/shared.js` — Utility Core & Financial Precision
- **What it does:** Provides the foundation for DOM manipulation (`$`, `node`), error notifications (`notice`), standardized fetch requests (`request`), and currency formatting (`money`).
- **Why it’s written this way:**
  - `money(paisa)` divides integer paisa by 100 and passes it to `Intl.NumberFormat('en-BD', {style: 'currency', currency: 'BDT'})`, ensuring consistent, localized Bangladeshi currency formatting (`BDT 1,850.00`).
  - `request(path, options)` standardizes error parsing: it handles FastAPI validation error arrays (e.g. `[{"loc": ["phone"], "msg": "..."}]`) and normalizes them into clean, human-readable strings before throwing.

---

### 4. `backend/app/commerce.py` — State Machine & Checkout Security
- **What it does:** Implements the core order business logic, lifecycle state transitions, cryptographic link token issuance, and confirmation processing.
- **Why it’s written this way:**
  - **Security by Design:** Plaintext tokens (`token = secrets.token_urlsafe(32)`) are sent only to the client. The database stores only `sha256(token)`. If the database is compromised, active checkout links cannot be forged.
  - **Enforced Transitions:** The `TRANSITIONS` dictionary defines allowed status moves. For example, an order cannot jump from `draft` to `shipped` without first being `confirmed` and `packed`.
  - **Version Locking:** If the seller alters items or prices in an order draft, `value["version"] += 1` increments, and all previously issued checkout links are automatically revoked (`revoked = 1`).
- **Data Flow:**
  - `create_link()`: Verifies draft status, invalidates old links, generates a 32-byte token, hashes it, and stores it in `checkout_sessions`.
  - `confirm_checkout()`: Executes inside a `BEGIN IMMEDIATE` SQLite transaction. Validates the version, calls `inventory.consume()` to decrement stock, marks the order `confirmed`, and creates a domain-separated tracking token (`tracking-v1:`).

---

### 5. `backend/app/inventory.py` — Atomic Inventory & Optimistic Locking
- **What it does:** Manages catalog variants (product, size, color), pricing, available stock, and stock movements.
- **Why it’s written this way:**
  - **Atomicity:** `consume()` executes `UPDATE variants SET stock=stock-?, version=version+1 WHERE id=? AND stock>=? AND active=1`. By combining the quantity check and decrement into a single SQL statement, race conditions and overselling are physically impossible.
  - **Optimistic Concurrency:** `update_variant()` requires `expected_version`. If a concurrent order confirmation occurred between loading and saving, the version mismatch rejects the edit with `409 Conflict`.
  - **Idempotency:** Stock restorations check `stock_movements WHERE event='restore'`. Even if a restock button is clicked twice, returned units are only credited once.

---

### 6. `backend/app/extractor.py` — Substring Hallucination Guard
- **What it does:** Connects to the Gemini API with structured output schemas to extract order details from conversational chats.
- **Why it’s written this way:**
  - **Zero-Hallucination Guard:** LLMs often make up plausible-sounding addresses or names when chats are ambiguous. In `validate_extraction()`, Python explicitly checks:
    ```python
    if value is not None and normalize_digits(value) not in source:
        values[field] = None
        warnings.append(f"Unsupported {field}: value not present in message.")
    ```
    Every extracted string *must* be an exact substring of the original message (after digit normalization). If the model hallucinates, the field is discarded with an honest warning banner.

---

## Part 2: 15 Likely Technical Interview Questions & Answers

### 1. Frontend Architecture & Framework Choice
**Q: Why did you build this with Vanilla JavaScript and native ES Modules instead of React or Next.js?**  
**A:** "For this specific problem, vanilla ES modules are technically superior. In Bangladesh, buyers open checkout links directly inside Facebook Messenger’s embedded in-app browser over mobile data (often 3G). A React or Next.js bundle introduces 100–300 KB of framework runtime, hydration delays, and parsing overhead. With semantic HTML, modular CSS, and native ES modules, our entire buyer checkout bundle is under 15 KB, loads in under 200 ms, and has zero build tool dependency or vulnerability footprint."

---

### 2. State Management
**Q: How do you manage state across the seller dashboard without Redux, Zustand, or React Context?**  
**A:** "I use a single source of truth pattern in `seller.js`. State is held in plain variables: `orders` array, `catalog` array, `selected` order object, and booleans for `dirty` and `busy`. UI renders are driven by pure functions: `renderOrders()` renders the order cards, `renderCatalog()` updates the variant pickers, and `selectOrder(order)` populates the editor drawer. Whenever data changes on the server, `refresh()` fetches fresh state and cleanly re-renders the DOM nodes using `replaceChildren()`."

---

### 3. Financial Precision
**Q: Why do your API schemas and frontend calculate prices in paisa rather than decimal BDT?**  
**A:** "JavaScript and Python floating-point numbers follow IEEE 754 standards, where operations like `0.1 + 0.2` yield `0.30000000000000004`. In e-commerce, floating-point rounding errors cause discrepancies in totals, tax, and ledger reconciliation. By representing all currency values as integer paisa (where 100 paisa = 1 BDT), all additions, multiplications, and aggregations are 100% exact integer arithmetic. The frontend only converts to decimals for user display via `money()`."

---

### 4. Form Validation & UX
**Q: How do you handle phone number and address validation for Bangladeshi users?**  
**A:** "In Bangladesh, buyers type numbers with various prefixes (`+8801...`, `8801...`, `01...`), spaces, or even Bangla numerals (`০১৭১...`). In `normalize.py`, we translate Bangla digits (`০-৯` to `0-9`), strip non-digits, normalize prefixes to standard `01...`, and validate against the regex `^01[3-9]\d{8}$`. On the buyer form, we also use `inputmode="tel"` so mobile keyboards automatically open the numeric keypad."

---

### 5. Security & Authentication
**Q: How does the seller authentication and session system protect against CSRF and session hijacking?**  
**A:** "Sellers authenticate with a configured access key, which the server exchanges for an 8-hour HttpOnly, SameSite=Strict session cookie. The cookie cannot be accessed by client-side JavaScript, protecting against XSS token theft. For mutating requests (`POST`, `PUT`, `DELETE`), the client must send an `X-CSRF-Token` header containing a SHA-256 token derived from the session (`sha256('seller-csrf-v1:' + token)`). The backend also validates the `Origin` header against `request.base_url` to block cross-origin requests."

---

### 6. Concurrency & Race Conditions
**Q: What happens if two buyers confirm the last available unit of an item at the exact same second?**  
**A:** "The system is protected by atomic database constraints. In `inventory.py`, the deduction is executed in a single SQL statement:
`UPDATE variants SET stock=stock-?, version=version+1 WHERE id=? AND stock>=? AND active=1`.  
Because SQLite runs this inside a `BEGIN IMMEDIATE` transaction, the first transaction succeeds and decrements stock to 0. The second transaction finds `stock >= 1` false, modifies 0 rows, and immediately triggers an HTTP 409 Conflict, rolling back the order and prompting the buyer that the item was just sold out."

---

### 7. Responsiveness & Mobile Design
**Q: How did you ensure the buyer checkout flow feels native on mobile screens?**  
**A:** "I designed the buyer interface mobile-first using CSS Grid and Flexbox. The viewport meta tag is configured with `viewport-fit=cover`. Form hit targets follow the 44px minimum touch target rule, font sizes on inputs are at least 16px to prevent iOS Safari auto-zooming, and visual elements use high-contrast text and border tokens defined in `tokens.css`. DevTools viewport testing confirms smooth layouts across 360px to 414px mobile widths."

---

### 8. Performance & Zero-Build
**Q: How did you optimize frontend performance without Webpack or Vite minification?**  
**A:** "Because our codebase does not import heavy NPM dependencies, the raw file sizes are tiny: `buyer.html` is 3 KB, `buyer.js` is 3.5 KB, and `styles.css` is 28 KB. Furthermore, FastAPI serves static files with `Cache-Control: no-store` for sensitive session pages and pre-connects Google Fonts. The entire page requires only 4 network requests on first load and renders in under 200 ms."

---

### 9. Token Security
**Q: Why don't you store the checkout token directly in the database?**  
**A:** "Following the same security best practice used for passwords and API tokens, we store only the SHA-256 hash of the checkout token in SQLite. When a buyer visits `/checkout/<token>`, the server hashes the URL token and looks up `WHERE token_hash = ?`. Even if someone gains read access to the database or a backup file, they cannot impersonate active buyer checkout links."

---

### 10. AI Hallucination Guard
**Q: What prevents the Gemini extractor from inventing customer names or delivery addresses?**  
**A:** "Prompt engineering alone is insufficient to prevent hallucinations. In `backend/app/extractor.py`, we added a deterministic verification layer: after Gemini outputs JSON, Python checks whether each string field is a literal substring of the normalized input chat. If the LLM generates a name or phone number not present in the customer's message, our backend forcefully nullifies the field and flags a warning. We never trust LLM output implicitly."

---

### 11. Error Handling & User Feedback
**Q: How does the UI handle network drops or server errors?**  
**A:** "Every asynchronous user action is wrapped in a `try...catch...finally` block. During requests, buttons show animated loading spinners (`<span class="spinner"></span>`) and are disabled to prevent duplicate submissions. If an error occurs, the standardized error message from the backend is rendered in a prominent `#notice` banner with `role="status"` for screen readers, and the button state is restored."

---

### 12. State Machine Violations
**Q: What happens if a seller attempts to jump an order directly from `draft` to `shipped`?**  
**A:** "Both the frontend and backend strictly prevent this. In `seller.js`, the `#next-status` dropdown only displays valid next statuses dictated by the `transitions` dictionary. If a malicious client bypasses the UI and sends an arbitrary status via API, `backend/app/commerce.py` validates the request against `TRANSITIONS[value['status']]` and throws an HTTP 409 Conflict error with 'Invalid order status transition'."

---

### 13. Data Export Security
**Q: You have a CSV export feature. How do you prevent CSV formula injection (CSV Injection / DDE)?**  
**A:** "In `backend/app/export.py`, before any customer name, product, or address string is written to a CSV cell, we check if it starts with formula-trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`). If detected, we prefix the cell with a single quote (`'`), neutralizing executable Excel macros. We also prepend a UTF-8 BOM (`\xef\xbb\xbf`) so Excel renders Bangla characters cleanly instead of showing garbled symbols."

---

### 14. What Was the Hardest Bug You Solved?
**Q: Can you describe a challenging technical bug you ran into during development and how you solved it?**  
**A:** "A tricky bug was handling buyer retries on flaky mobile connections. If a buyer tapped 'Confirm' on a slow 3G connection and refreshed or retried, the second request could either fail because the link was already marked confirmed, or worse, try to deduct stock a second time. I solved this by storing a `confirmed` flag and tracking link on the checkout session. On a retry, the endpoint detects `confirmed == 1` and idempotently returns the existing receipt without touching stock or creating duplicate records."

---

### 15. Future Improvements & Scaling
**Q: If you had another two weeks to work on this, what would you improve next?**  
**A:** "Three clear priorities:
1. **Direct Courier API Integration:** Connecting directly to Steadfast and Pathao APIs to automatically book consignments and receive automated webhook tracking updates.
2. **PostgreSQL Migration:** Transitioning from SQLite to PostgreSQL for multi-region cloud scaling and multi-tenant connection pooling.
3. **PWA & Offline Draft Caching:** Adding a Service Worker and IndexedDB to allow sellers to draft orders offline during internet drops and sync when connectivity returns."

