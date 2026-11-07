<div align="center">

# 🛒 F-Commerce Order Extractor (Order Desk)

**Transforming chaotic Messenger chats into structured, reviewable orders for Bangladeshi social commerce.**

*Zero-install mobile checkout · Real-time inventory tracking · Resilient FastAPI + SQLite engine*

<br />

[![Tests](https://img.shields.io/badge/offline_tests-241_passing-2ea44f?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/MirajHossain22/fcommerce-order-extractor)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Status](https://img.shields.io/badge/Status-Live_Demo-success?style=for-the-badge)](https://fcommerce-order-extractor.onrender.com/)

<br />

🌐 **[Live Demo](https://fcommerce-order-extractor.onrender.com/)** &nbsp;·&nbsp; 📖 **[Interactive API Docs](https://fcommerce-order-extractor.onrender.com/docs)** &nbsp;·&nbsp; 🟢 **[Health Check](https://fcommerce-order-extractor.onrender.com/healthz)**

</div>

<br />

> [!IMPORTANT]
> ### 🔑 Reviewer Access Instructions
> - **Live Storefront URL:** [https://fcommerce-order-extractor.onrender.com/](https://fcommerce-order-extractor.onrender.com/)
> - **Seller Access Key:** Use the demo key provided in the submission form (`<DEMO_SELLER_KEY>`).
> - **One-Click Reviewer Login:** When you open the live link, click the **"⚡ Fill Demo Key"** button located right on the login screen to enter the seller workspace in one click.
> - *Note on Cold Starts:* The application is hosted on Render’s free tier container. If inactive, the container may take 30–45 seconds to wake up.

---

## 📌 The Problem

In Bangladesh, over 80% of independent online retail happens through Facebook pages and Messenger threads. While messaging is natural for buyers, it creates three major operational problems for sellers:

1. **Misplaced and Incomplete Orders:** Customer addresses and phone numbers are buried in conversational chat histories ("Bhai Uttara pathan"). Critical delivery details are often missing or miscopied.
2. **Stock Tracking Errors:** Sellers agree to orders in chat without knowing if that specific size or color is still available, leading to overselling and embarrassing cancellations.
3. **Delivery Status Anxiety:** Customers repeatedly ping sellers ("Bhai parcel kothay?") because there is no transparent tracking channel. Both sides waste hours taking screenshots and searching old chat threads.

---

## 💡 The Solution

**Order Desk** is a lightweight, mobile-first ordering bridge that preserves the convenience of conversational selling while eliminating administrative chaos.

- **Zero-Install Mobile Checkout:** Sellers generate a private, time-limited checkout link (`/buy/<token>`). The customer opens the link inside Messenger without installing an app or creating an account, reviews the Cash on Delivery (COD) total, confirms their delivery address in 30 seconds, and receives a digital receipt with a private tracking page (`/track/<token>`).
- **Real-Time Stock Protection:** Orders link directly to catalog variants (size/color). Stock is decremented in an atomic SQLite transaction upon confirmation.
- **Structured Seller Desk:** A desktop-optimized dashboard with live order statistics, client-side search/filtering, and an enforced progression state machine (`Draft` $\rightarrow$ `Confirmed` $\rightarrow$ `Packed` $\rightarrow$ `Shipped` $\rightarrow$ `Delivered`).

---

## ✨ Features

### 🌟 Core Feature: Mobile-First Private Checkout & Confirmation
- **Tokenized Security:** Generates cryptographically random 32-byte checkout tokens. Only their SHA-256 hashes are stored in SQLite.
- **Anti-Tamper Version Locking:** If a seller alters items or prices after sending a link, older links are automatically revoked to prevent pricing disputes.
- **Bilingual & Responsive UI:** Clear, high-contrast mobile layout designed for 360px–414px smartphone screens with bilingual English and Bengali helper instructions.
- **Validation Guard:** Normalizes Bangla numerals (`০-৯` to `0-9`) and validates Bangladeshi 11-digit mobile numbers (`01XXXXXXXXX`).

### 📦 Supporting Feature 1: Catalog Management & Atomic Stock Deduction
- **Size & Color Variants:** Multi-variant tracking per product with individual pricing and stock counters.
- **Optimistic Concurrency:** Protects catalog edits with `expected_version` locking to prevent race conditions.
- **Idempotent Restocking:** If a parcel is returned, sellers can inspect the goods and restock inventory with a single click, protected against double-restoration.
- **Low-Stock Warnings:** Real-time visual alerts when variant stock falls to $\le 5$ units.

### 📋 Supporting Feature 2: Structured Fulfillment State Machine
- **Strict State Progression:** Orders transition predictably through `draft` $\rightarrow$ `confirmed` $\rightarrow$ `packed` $\rightarrow$ `shipped` $\rightarrow$ `delivered`.
- **Courier Delivery Tracking:** Sellers can enter courier names (e.g. Steadfast, Pathao) and consignment tracking IDs, which immediately render on the buyer's private tracking link.
- **Integer Paisa Financial Math:** All totals and fees are calculated in integer paisa (100 paisa = 1 BDT) to avoid floating-point math bugs.

### 🤖 Supporting Feature 3: AI Chat Order Extractor
- **Conversational Parsing:** Sellers can paste raw, informal Bangla, Banglish, or English chat messages to generate pre-filled drafts.
- **Substring Hallucination Guard:** Python validates that every extracted string field is an exact substring of the original chat, dropping unverified data to prevent AI hallucinations.

---

## 🛠️ Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Frontend** | Vanilla JavaScript (ES Modules), Semantic HTML5, CSS3 Tokens | Zero build tools, zero bundle bloat. Loads under 200 ms on 3G mobile. |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn | High-performance asynchronous API with strict input bounds and typing. |
| **Database** | SQLite3 with Write-Ahead Logging (WAL) | Single-file persistence with atomic transactions (`BEGIN IMMEDIATE`). |
| **AI / NLP** | Google Gemini API + Substring Verification Guard | Structured JSON chat extraction with deterministic hallucination filters. |
| **Testing** | Pytest, AnyIO, Node CDP scripts | 241 offline tests covering concurrency, CSRF, and data integrity. |
| **Deployment** | Docker, Render Cloud | Containerized production deployment. |

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- Git

### Quick Setup

```powershell
# 1. Clone repository
git clone https://github.com/MirajHossain22/fcommerce-order-extractor.git
cd fcommerce-order-extractor

# 2. Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
Copy-Item .env.example .env
```

Edit `.env` to configure your seller access key:
```env
SELLER_API_KEYS={"<DEMO_SELLER_KEY>":"local-shop"}
```

```powershell
# 5. Seed realistic demo data (products, variants, sample orders)
python scripts/seed_demo.py

# 6. Run the server
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000/** in your browser and log in with `<DEMO_SELLER_KEY>`.

---

## 🧪 Testing & Verification

The test suite runs completely offline without network dependencies or third-party API credentials:

```powershell
pytest
```
*Result: 241 passed in ~6.5 seconds.*

---

## 📸 Screenshots & Workflow

| Seller Workspace | Mobile Buyer Checkout |
|:---:|:---:|
| *(Screenshot Placeholder: Order Desk with stats, orders list, and line item editor)* | *(Screenshot Placeholder: Mobile responsive checkout summary and address form)* |

| Buyer Tracking Page | Catalog & Stock Tracking |
|:---:|:---:|
| *(Screenshot Placeholder: Live status timeline and courier reference card)* | *(Screenshot Placeholder: Variant inventory table with low-stock badges)* |

---

## ⚠️ Limitations & Next Steps

### Current Limitations
- **Courier API Synchronization:** Courier tracking details (consignment ID and courier name) are entered by the seller; there is currently no direct webhook sync with Steadfast or Pathao APIs.
- **Single-Node SQLite:** Suitable for up to hundreds of daily orders per shop, but horizontal cloud scaling across multiple instances requires migrating to PostgreSQL.
- **Provider Quota:** Live Gemini extraction depends on Google API quota; the manual draft builder and checkout flows are architected to work independently without AI dependencies.

### Next Steps
1. **Automated Courier APIs:** Integrate direct booking and status webhooks with Steadfast, RedX, and Pathao.
2. **PostgreSQL Migration:** Transition database driver for multi-tenant cloud scaling.
3. **PWA & Offline Drafts:** Add IndexedDB caching to enable offline order drafting during connectivity drops.

