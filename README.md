# fcommerce-order-extractor

Convert Bangla, Banglish, and English seller chat messages into structured orders.

See [the step-by-step execution plan](EXECUTION_PLAN.md) for verified progress, remaining work, and the new Messenger checkout-link idea, including buyer confirmation, tracking, saved addresses, and stock management.

The seller dashboard, browser sessions, checkout links, buyer form, retry-safe confirmation, receipts, and private status tracking are implemented for local use. See [the setup and usage guide](BACKEND_CHECKOUT.md). Configure `SELLER_API_KEYS` separately from the AI provider's `API_KEY`, start FastAPI, and open `http://127.0.0.1:8000/`. Seller APIs accept `Authorization: Bearer <seller-key>`; the dashboard exchanges the key for an HttpOnly session cookie. Buyer links need no seller key. Courier API integration remains planned work.

Seller-entered courier details now appear on buyer tracking pages. [Pilot operations and deployment preparation](DEPLOYMENT.md) covers verified backup/restore tooling, persistent storage, the deployment launcher, and the container starter. Hosting and real HTTPS validation remain pending.

[Catalog and stock management](INVENTORY.md) now supports size/color variants, confirmation-time stock deduction, cancellation restoration, and inspected-return restocking. Manual items remain explicitly untracked.

Phases 1–3 provide the order schema, digit/phone normalization, environment configuration, Gemini extraction, a command-line interface, FastAPI endpoints, SQLite storage, CSV export, and tests with mocked LLM calls.

## Day 1 verification

Phases 1–2 are implemented. The offline suite passed all 94 tests on October 27, 2026, including mocked extraction and command-line checks.

The 12-message live check is deferred at the user's request after model availability errors, a provider high-demand response, and a network error or timeout. No live cases completed; model accuracy and live null preservation remain unverified. Mocked test results must not be presented as live extraction accuracy.

## Setup (Python 3.11+, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pytest -q
```

Set `PROVIDER`, `MODEL`, and `API_KEY` in `.env` when configuring extraction. `load_settings()` reads the root `.env`; existing environment variables take precedence. Blank settings fail validation. Tests use fabricated settings and require no API credentials or network access. Never commit `.env`.

## Phase 1 behavior

- `Order` requires an explicit boolean `is_order`. Missing extracted fields default to `null`; quantity must be a positive integer when supplied.
- `normalize_digits()` converts Bangla digits to English digits.
- `normalize_phone()` returns `(phone, warnings)`, strips whitespace/dashes, converts `+880` or `880` to `0`, and validates `^01[3-9]\d{8}$`. Invalid input returns `None` with a warning. Missing input returns `None` without a warning.
- Normalize phone candidates before constructing `Order`, passing along any warnings. The schema accepts only normalized phones.
- All test data is synthetic. Repeated-zero phone fixtures exist solely for format validation; they are never used to contact anyone.

`backend/app` holds implementation, `backend/tests` holds tests, `eval` contains the evaluation dataset and tooling, and `frontend` contains the seller dashboard and buyer checkout/tracking pages.

## Phase 2: extract from the command line

Set `PROVIDER=gemini`, `MODEL` to your Gemini model ID, and `API_KEY` to your Gemini API key in `.env`. The model must support structured JSON output. Only Gemini is implemented in this phase; unsupported providers fail explicitly. There are no new dependencies.

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -X utf8 -m app.extractor "bhai TEST_PRODUCT 2 ta lagbe, name TEST_CUSTOMER, address TEST_ADDRESS_000, phone 00000"
```

The command prints one order as JSON, including `warnings`. Omitting the message reads stdin. Errors go to stderr with exit code 1. Live extraction sends the supplied message to Gemini; use only synthetic messages.

The request uses Gemini's [structured JSON output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en) with a Pydantic schema. Malformed model JSON or schema violations get exactly one retry. HTTP errors, timeouts, and blocked/incomplete responses raise errors without retrying. Invalid source phones become `null` with a warning, without triggering a retry.

The prompt forbids guessing names, phones, addresses, or other missing values. Text fields must be exact source substrings; unsupported text is discarded with a warning. Non-orders return null order fields. Quantity defaults to null, and only explicit positive quantities are requested. Classification and quantity interpretation still depend on the model; passing mocked tests does not establish live extraction accuracy.

`backend/tests/test_extractor.py::test_synthetic_message_plumbing` contains ten synthetic orders in Bangla, Banglish, English, and mixed text plus two non-orders. These tests use mocked outputs to check validation and null preservation. To check the model by hand, run those messages individually through the CLI and compare every field against the source; omit names, phones, addresses, and quantities in some messages and verify that they remain null. Live checks require a configured `.env` and are separate from the offline test suite.

## Phase 3: API, storage, and CSV

Install the updated requirements, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` to try the endpoints with synthetic messages.

| Endpoint | Request body | Response |
| --- | --- | --- |
| `POST /extract` | `{"message":"TEST_PRODUCT 2 ta chai"}` | One extracted order, including null fields and warnings |
| `POST /extract/batch` | `{"messages":["TEST_PRODUCT 2 ta chai","hello"]}` | Extracted results in input order |
| `GET /orders` | None | Saved orders in insertion order |
| `GET /orders/export.csv` | None | Downloadable `orders.csv` |

Extraction automatically saves only results with `is_order=true`. Non-orders are returned without being saved. A batch saves its orders in one SQLite transaction after every extraction succeeds; an extraction failure saves none of that batch. Repeating a successful POST creates additional rows; there is no deduplication.

SQLite uses Python's built-in `sqlite3`. The ignored `orders.sqlite3` file is created in the repository root on API startup, and orders survive restarts. The CLI remains extraction-only. Listing and exporting stored orders do not require Gemini credentials.

CSV contains all order fields, including `warnings` as a JSON array. Nulls become empty cells; a UTF-8 BOM preserves Bangla text in spreadsheet applications. CSV quotes commas, quotes, and newlines. Import the phone column as text to retain leading zeros.

Blank messages, empty batches, invalid types, and unknown request fields return HTTP 422. Missing or invalid LLM settings return 503. Provider or extraction failures return 502 without including credentials or raw provider output.

Run `.\.venv\Scripts\python.exe -m pytest -q` for the offline suite. Phase 3 verification: **118 passed**. Tests use temporary databases and mocked LLM calls; no API credits are needed. The installed Starlette test client emits an upstream deprecation warning for its `httpx` integration; the tests currently pass. Live model accuracy remains unverified, and the evaluation dataset and scoring are deferred to Phase 4.

## Phase 4: evaluation

`eval/dataset.jsonl` contains 50 user-authored messages: 15 clean, 15 messy, 10 in the supplied `mixed` category, 5 missing key fields, and 5 non-orders. Names and addresses were replaced with clearly synthetic labels in both messages and expected outputs; Bangla labels retain Bangla script. The location mentioned in a non-order question was also replaced. Other labels and phone fixtures were preserved, and `notes: null` was added to every expected output.

Each nonblank line must be one JSON object with `message` and `expected`. Optional string fields `id` and `category` are preserved in failure reports but are not scored or sent to the LLM. Include all seven scored fields explicitly, using JSON `null` for missing information:

```json
{"message":"TEST_PRODUCT ২টা চাই, phone 00000","expected":{"is_order":true,"customer_name":null,"phone":null,"address":null,"product":"TEST_PRODUCT","quantity":2,"notes":null}}
{"message":"hello, কেমন আছেন?","expected":{"is_order":false,"customer_name":null,"phone":null,"address":null,"product":null,"quantity":null,"notes":null}}
```

These two format examples are not the evaluation dataset. Use obviously synthetic names, addresses, and phone fixtures. Expected phones must already be normalized; invalid phones are `null`. Expected quantities must be positive integers or `null`. `notes` must be present, even when null. Optional `warnings` are accepted but not scored.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -X utf8 eval/run_eval.py
```

The evaluator validates the whole file before calling Gemini, then writes `eval/results.md`. It accepts any nonempty dataset size so you can check a small subset first; 50 messages is the planned dataset size, not a program restriction. To preserve a run, choose a separate output path:

```powershell
.\.venv\Scripts\python.exe -X utf8 eval/run_eval.py --dataset eval/dataset.jsonl --output eval/results-first.md
```

Metrics use exact equality, including nulls, case, and whitespace. There is no fuzzy comparison or normalization of labels during scoring:

- **Per-field accuracy:** correct values for that field divided by all dataset messages.
- **Overall accuracy:** messages with all seven fields correct divided by all dataset messages.
- **Mean field accuracy:** correct values across all seven fields divided by seven times the message count.

Every mismatch is listed with its message, expected output, actual output, and mismatched fields. Extraction errors count as incorrect for all seven fields and appear in the failure list; remaining messages are still evaluated. This makes the score an end-to-end measure when provider failures occur. Matching nulls count as correct, so inspect the failure list alongside aggregate scores.

Invalid or empty datasets leave an existing report untouched and exit with code 1. A completed run with extraction errors saves the report and exits with code 1; a completed run without extraction errors exits with code 0, even if some predictions are wrong. Default runs replace `eval/results.md`.

Phase 4 offline verification: **139 tests passed**, including hand-calculated scoring, failures, nulls, dataset validation, metadata handling, and report output. The imported dataset passes validation. The first live run attempted all 50 messages but produced 50 extraction errors and no usable predictions; see `eval/results-first.md`. Its 0% end-to-end score is not a model-accuracy measurement. A separate diagnostic request returned HTTP 429 and reported an exhausted free-tier daily request limit of 20 for the configured model. The evaluator did not retain individual error causes, so not all run failures can be attributed to quota exhaustion. The supplied category labels are preserved, including some entirely Bangla messages labeled `mixed`.

## Phase 5: regex baseline

The local regex extractor in `eval/baseline.py` provides a deterministic comparison that needs no credentials or network calls. Run it against the same dataset:

```powershell
.\.venv\Scripts\python.exe -X utf8 eval/run_eval.py --extractor regex
```

The first baseline run scored **46.00% whole-order accuracy (23/50)** and **83.43% mean field accuracy**, with zero extraction errors. Results and individual mismatches are in `eval/results-baseline.md`. The baseline uses only explicit labels and a small set of English, Banglish, and Bangla patterns; it intentionally does not use the expected labels during extraction.
