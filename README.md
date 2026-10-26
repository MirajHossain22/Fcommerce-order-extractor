# fcommerce-order-extractor

Convert Bangla, Banglish, and English seller chat messages into structured orders.

Phases 1–2 provide the order schema, digit/phone normalization, environment configuration, Gemini extraction, a command-line interface, and mocked tests. The API arrives in Phase 3.

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

`backend/app` holds implementation, `backend/tests` holds tests, and `eval` and `frontend` are reserved directories for later phases.

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
