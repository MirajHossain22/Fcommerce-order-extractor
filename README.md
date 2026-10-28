# fcommerce-order-extractor

Turn messy Bangla, Banglish, and English Facebook or WhatsApp seller messages into structured, reviewable orders. The project combines validated Gemini extraction with a deterministic regex baseline, a FastAPI/SQLite backend, evaluation tooling, and mobile seller/buyer workflows.

> Portfolio status: the complete local MVP is implemented and covered by 218 offline tests. Live Gemini accuracy is not yet measured because the recorded evaluation run hit provider failures/quota; the manual checkout flow works without Gemini.

## What it does

- Extracts `is_order`, customer name, phone, address, product, quantity, notes, and warnings.
- Converts Bangla digits and validates Bangladeshi phone numbers without inventing missing information.
- Saves order drafts to SQLite and exports seller-owned orders as CSV.
- Lets a seller review AI output or create a draft manually, then share a private checkout link.
- Lets a buyer confirm delivery details once, receive a receipt, and follow a private tracking page.
- Tracks order status, courier references, product variants, and stock changes.
- Measures exact field/order accuracy on a 50-message synthetic dataset and compares Gemini with a regex baseline.

All committed examples and test fixtures are synthetic. `.env`, SQLite databases, and backups are ignored by Git.

## Architecture

```text
Seller chat -> Gemini extractor -> Pydantic validation -> reviewable draft
                                      |                    |
                               eval + baseline       checkout link
                                                          |
Buyer confirmation -> SQLite transaction -> receipt/tracking/status/inventory
```

- `backend/app/`: extraction, normalization, API, auth, checkout, inventory, backup, and serving code.
- `backend/tests/`: offline unit, integration, security, persistence, and workflow tests.
- `frontend/`: responsive seller dashboard and buyer checkout/tracking pages.
- `eval/`: synthetic dataset, evaluator, regex baseline, and saved reports.

## Run locally with Python 3.11+

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`: choose a current Gemini model, add the provider API key, and create a seller key. The seller key is separate from the Gemini key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add the result as JSON, for example `SELLER_API_KEYS={"generated-long-key":"local-shop"}`. Then start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the seller dashboard or `/docs` for the API. Extraction needs Gemini settings; manual drafts and checkout do not.

## Run locally with Docker Compose

Keep provider settings in the ignored `.env`, then set the seller mapping for Compose and start the app:

```powershell
$env:SELLER_API_KEYS = '{"generated-long-key":"local-shop"}'
docker compose up --build
```

Open `http://127.0.0.1:8000/`. SQLite data is kept in the `order-data` named volume. Stop with `docker compose down`; do not add `--volumes` if you want to retain orders.

## CLI and API

Extract one synthetic message from the command line:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -X utf8 -m app.extractor "TEST_PRODUCT 2 ta chai"
```

Core endpoints include `POST /extract`, `POST /extract/batch`, `GET /orders`, `GET /orders/export.csv`, seller draft/checkout/catalog routes, and public tokenized buyer checkout/tracking routes. Seller routes require a bearer key or browser session. See [BACKEND_CHECKOUT.md](BACKEND_CHECKOUT.md) for the complete local workflow and [INVENTORY.md](INVENTORY.md) for stock behavior.

## Tests and evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -X utf8 eval/run_eval.py --extractor regex
.\.venv\Scripts\python.exe -X utf8 eval/run_eval.py
```

GitHub Actions runs the offline suite on Python 3.11 and 3.12. The live evaluator requires Gemini credentials and consumes provider quota.

| Extractor | Exact whole order | Mean field | Extraction errors |
| --- | ---: | ---: | ---: |
| Regex baseline | 46.00% (23/50) | 83.43% | 0 |
| Gemini | Not measured | Not measured | Recorded run failed all 50 requests |

See [results-baseline.md](eval/results-baseline.md) for baseline failures and [results-first.md](eval/results-first.md) for the unsuccessful provider run. Matching `null` values count as correct, so individual failures remain important alongside aggregate scores.

## Extraction guarantees

- The prompt explicitly forbids guessing names, phones, addresses, or other missing fields.
- Missing quantity is `null`, never an assumed `1`.
- Non-orders return `is_order=false` and null order fields.
- Bangla digits are converted to English digits.
- Phones are stripped of spaces/dashes, `+880`/`880` is converted to `0`, and only `^01[3-9]\d{8}$` is accepted.
- Invalid phones become `null` and add a warning; malformed model JSON is retried once.

## Current limits

- Successful live Gemini accuracy still needs to be measured after provider access/quota is available.
- SQLite is intentionally configured for one app instance/worker, not horizontal scaling.
- Courier details and order statuses are seller-entered; there is no courier API or Messenger automation.
- Saved buyer addresses/accounts are not implemented.
- Hosting and a real-user pilot are not complete. The Docker image and persistent local volume have been verified; [DEPLOYMENT.md](DEPLOYMENT.md) documents recovery and optional hosting preparation.

## Demo flow

1. Sign in to the seller dashboard and create or extract a synthetic draft.
2. Review the fields and create a checkout link.
3. Open the link in a private/mobile window, enter synthetic buyer details, and confirm.
4. Update the order from the seller dashboard and refresh the buyer tracking page.
5. Export the seller's orders as CSV.

For implementation history and clearly separated later work, see [EXECUTION_PLAN.md](EXECUTION_PLAN.md).
