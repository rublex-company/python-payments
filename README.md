# rublexpayments

Python SDK for the [Rublex Payment Gateway](https://panel.pay.rublex.io) — accept crypto and fiat payments through a single, terminal-scoped API.

Wraps every endpoint of the Rublex Merchant API with a thin client, plus a fluent invoice builder. Mirrors the [Laravel SDK](https://github.com/rublex-company/laravel-payments) and the [Node SDK](https://github.com/rublex-company/node-payments).

## Requirements

- Python **3.8+**
- [`requests`](https://pypi.org/project/requests/) `>= 2.25`

## Installation

```bash
pip install rublexpayments
```

## Build Your Integration With an AI Assistant

**Skip reading the rest of this doc.** Paste this whole `README.md` plus the prompt below into Claude / Cursor / Copilot — the assistant interviews you, then wires the SDK into your Python project end to end.

```text
ROLE
You are a senior Python engineer. Your task is to integrate the Rublex Payment
Gateway into my Python project using the official `rublexpayments` SDK (README
provided above) and take me from zero to a production-ready integration.

SOURCE OF TRUTH
The `rublexpayments` README provided above is your single source of truth.
  - USE the SDK. Do not hand-roll a requests/httpx client or call the REST API.
  - Only call methods that exist in the README's endpoint reference table
    (`crypto()`, `fiat()`, `get_supported_currencies()`, `get_crypto_invoice()`,
    `get_fiat_invoice()`, `list_fiat_invoice_gateways()`, `select_fiat_gateway()`).
  - Signatures are in the README — respect them exactly. Crypto creation takes
    ONE argument now (`create_crypto_invoice(data)`), no payer-choice flag.
  - Every SDK call returns the `{"status", "message", "data"}` envelope as a
    `dict`. Wrap that handling centrally.
  - Hosted invoice pages live on https://panel.pay.rublex.io and are baked into
    the `data["invoice_url"]` you receive. Redirect customers there as-is.
  - If something I ask for is not in the SDK or the README is silent on it,
    STOP and tell me. Never invent endpoints or response fields.

CRYPTO INVOICE — NON-NEGOTIABLE PRE-FLIGHT
Before you call `client.crypto().…create_invoice()` (or
`client.create_crypto_invoice(data)`) you MUST:
  1. Call `client.get_supported_currencies()` first.
  2. Pick a `currency_id` from THAT response (terminal-approved list).
  3. Pass it via `.pick(currency_id)` or as `data["currency_id"]`.
Never hard-code numeric currency IDs. The terminal rejects unapproved IDs with
HTTP 422 — surface a clear error and refetch the list on retry.

RETURN URLS — success_url AND failed_url
Every invoice flow accepts optional `success_url` / `failed_url` (builder
methods `.success(url)`, `.failed(url)`, or `.return_to(url)` for the same URL).
Pass them from the checkout. The redirect is UX only — NOT proof of payment.
Order state must come from the webhook + a server-side status lookup.

WORK IN TWO PHASES.

──────────────────────────────────────────────
PHASE 1 — INTERVIEW ME (no code yet)
Ask the questions below in ONE grouped message, recommend where you can, then
STOP and wait.
  1. Payment types: crypto, fiat, or both?
  2. Flow: explain the trade-offs and recommend one:
       - Crypto · Pay Request          (`client.crypto().pick(id).create_invoice()`)
       - Fiat · Direct gateway         (`client.fiat().pick(gateway_id).create_invoice()`)
       - Fiat · Gateway selection      (`client.fiat().by_payer().create_invoice()` + payer endpoints)
  3. Framework: Django / FastAPI / Flask / Starlette / Litestar / plain script?
     Sync or async? (The SDK is sync; if my app is async, recommend running
     SDK calls in a threadpool or via `anyio.to_thread.run_sync`.)
  4. ORM / DB layer: Django ORM, SQLAlchemy, Tortoise, Beanie, raw psycopg …
  5. Python version (3.8+ supported by the SDK).
  6. Where should the terminal token live? (`.env` via python-dotenv, AWS
     Secrets Manager, Vault, K8s secrets …)
  7. Which URL should be my `callback_url`, and which should `success_url` /
     `failed_url` point to? (Same URL for both is fine — recommended.)
  8. Scope: which pieces do I need — checkout endpoint that creates an invoice
     and redirects, webhook endpoint, Order/Payment model + migration, status
     reconciliation job (Celery / RQ / APScheduler / cron), admin view, tests?
  9. Greenfield or fitting into code I'll paste?
 10. Separate staging/production terminals?

──────────────────────────────────────────────
PHASE 2 — BUILD IT (after I confirm)
Deliverables, idiomatic for the stack chosen in Phase 1:
  a. SDK wrapper module — a thin `rublex_client.py` that constructs
     `RublexPayments.from_env()` once (module-level singleton) and exposes
     a small `payments_service` with envelope handling + logging. NO direct
     HTTP calls.
  b. Invoice creation
     - Crypto: call `get_supported_currencies()` (cache briefly with TTL via
       `functools.lru_cache` or framework cache), pick the right `currency_id`,
       create the invoice via the SDK with `amount`, `callback`, `success`,
       `failed`, persist `invoice_number` on the Order.
     - Fiat: same pattern with `pick(gateway_id)` or `by_payer()`.
     - Redirect / return `data["invoice_url"]` as-is.
  c. Webhook endpoint
     - Responds `200 OK` within 10s (defer heavy work to a queue / background task).
     - Treats the body as UNTRUSTED: re-fetch via `get_crypto_invoice()` /
       `get_fiat_invoice()` before marking paid.
     - Idempotent — guard by Order status before transitioning.
     - Maps PENDING / PARTIAL / PAID / EXPIRED / CANCELLED → order state.
  d. Return-URL endpoint
     - Reads `invoice_number` from the query string, looks up MY order, renders
       status from the local record. Never trust the redirect alone.
  e. Config + errors
     - Use `RublexPayments.from_env()` so env vars match the SDK defaults.
     - Centralised error handling for the documented HTTP codes (400, 401, 403,
       404, 422, 429, 5xx). Retry with exponential backoff on 429 / 5xx via a
       queued/background task — not in the request thread.
     - On 422 from crypto, refetch supported currencies and bubble a clear error.
     - Catch `RublexConfigError` and `RublexRequestError` explicitly.
  f. Security
     - Token only in env / secrets manager, never in client code or VCS.
     - Log `invoice_number` alongside my internal order id.
     - HTTPS on every URL (callback / success / failed).
  g. Optional but recommended: a Celery beat / cron task that pulls open
     invoices and reconciles their status — defends against missed webhooks.

OUTPUT FORMAT
  - Full file tree first, then each file in its own code block.
  - Migrations, models, views/routes, service, settings, tests.
  - Setup steps + env vars + how to run.
  - Finally, ask whether I want automated tests (pytest) or any adjustments.

Begin with PHASE 1 now.
```

> **Tip:** If you're on Django, also ask the assistant to register the webhook URL under a CSRF-exempt path; on FastAPI / Starlette, wrap the SDK calls in `anyio.to_thread.run_sync` so the event loop stays free.

## Configuration

The SDK needs your **terminal token** (a 60-char secret from *Stores → Terminals* in the merchant panel). Pass it explicitly or via environment variables.

```env
RUBLEX_PAYMENTS_API_KEY=<your-60-char-terminal-token>
RUBLEX_PAYMENTS_CALLBACK_URL=https://your-site.com/rublex/callback
# Override only if Rublex tells you to:
# RUBLEX_PAYMENTS_URL=https://api.pay.rublex.io/terminals/v1/
```

```python
from rublexpayments import RublexPayments

# Explicit
rublex = RublexPayments(
    api_key="<your-terminal-token>",
    callback_url="https://your-site.com/rublex/callback",
)

# Or pick up everything from the environment
rublex = RublexPayments.from_env()
```

> **Treat the terminal token like a password.** Keep it server-side only — never ship it to a browser or mobile app.

## Invoice creation

> **Crypto pre-flight is mandatory.** Before creating a crypto invoice you MUST call `get_supported_currencies()` and use one of the returned `id` values as `currency_id`. The terminal rejects IDs it has not approved with HTTP `422`. Do not hard-code IDs.

Two equivalent styles — pick whichever fits your code.

### Fluent builder

```python
# 1) Look up which currencies this terminal supports.
supported = rublex.get_supported_currencies()
currency_id = supported["data"][0]["id"]

# 2) Crypto · merchant-fixed coin
invoice = (
    rublex.crypto()
    .amount(0.5)
    .pick(currency_id)                                      # from /currencies/supported
    .callback("https://your-site.com/rublex/callback")
    .return_to("https://your-site.com/checkout/return")     # success + failure
    .create_invoice()
)

# Fiat · direct gateway
fiat = (
    rublex.fiat()
    .amount(19.99)
    .pick(4)                                                # gateway_id from /fiat/gateways
    .lock_rate()                                            # fixed FX rate
    .success("https://your-site.com/checkout/success")
    .failed("https://your-site.com/checkout/cancelled")
    .customer(email="buyer@example.com", first_name="Ada")
    .create_invoice()
)

# Fiat · gateway selection (payer picks the gateway on the hosted page)
fiat_pick = (
    rublex.fiat()
    .amount(19.99)
    .by_payer()
    .lock_rate(False)
    .return_to("https://your-site.com/checkout/return")
    .create_invoice()
)
```

### Direct methods

```python
supported = rublex.get_supported_currencies()["data"]

rublex.create_crypto_invoice({
    "amount": 0.5,
    "currency_id": supported[0]["id"],
    "success_url": "https://your-site.com/checkout/return",
    "failed_url":  "https://your-site.com/checkout/return",
})

rublex.create_fiat_invoice({
    "amount": 19.99,
    "gateway_id": 4,
    "success_url": "https://your-site.com/checkout/return",
    "failed_url":  "https://your-site.com/checkout/return",
})

rublex.create_fiat_invoice({
    "amount": 19.99,
    "success_url": "https://your-site.com/checkout/return",
    "failed_url":  "https://your-site.com/checkout/return",
}, payer_choice=True)                                       # gateway selection
```

Redirect the customer to `response["data"]["invoice_url"]` to complete payment.

> **`success_url` / `failed_url` are UX, not proof of payment.** Always reconcile against the webhook or `get_crypto_invoice()` / `get_fiat_invoice()`.

## Endpoint reference

| Group | Method | Endpoint |
|---|---|---|
| Terminal | `get_information()` | `GET /info` |
| Catalog | `get_currencies(page=None, per_page=None)` | `GET /currencies` |
| Catalog | `get_supported_currencies(page=None, per_page=None)` | `GET /currencies/supported` |
| Catalog | `get_fiat_gateways()` | `GET /fiat/gateways` |
| Catalog | `get_fiat_currencies()` | `GET /fiat/currencies` |
| Crypto | `create_crypto_invoice(data)` | `POST /pay-request` |
| Crypto | `get_crypto_invoice(invoice_number)` | `GET /invoices` |
| Crypto | `list_crypto_invoices(params=None)` | `GET /invoices` |
| Crypto | `list_pay_requests(params=None)` | `GET /pay-requests` |
| Fiat | `create_fiat_invoice(data, payer_choice=False)` | `POST /fiat/pay-request-direct` or `/fiat/pay-request-selection` |
| Fiat | `get_fiat_invoice(invoice_number)` | `GET /fiat/invoices` |
| Fiat | `list_fiat_invoices(params=None)` | `GET /fiat/invoices` |
| Payer | `list_fiat_invoice_gateways(invoice_number)` | `GET /fiat/invoices/{n}/gateways` |
| Payer | `select_fiat_gateway(invoice_number, data)` | `POST /fiat/invoices/{n}/select-gateway` |

Every method returns the gateway's shared envelope as a `dict`:

```python
{"status": "SUCCESS" | "ERROR", "message": "...", "data": { ... }}
```

## Webhooks

Set a `callback_url` (per-invoice or globally via the `callback_url` constructor arg). On status change Rublex `POST`s JSON to it:

```json
{ "invoice_number": "BpXo8T60vIN9D7NCcs66rOnZVipBLUah", "status": "PAID", "amount": "0.50000000", "paid_amount": "0.50000000", "currency": "USDT (TRC20)" }
```

Required behaviour:

1. Respond `200 OK` within 10 seconds.
2. Treat the callback as **untrusted** — re-fetch the invoice via `get_crypto_invoice` / `get_fiat_invoice` before marking the order paid.
3. Be **idempotent** — the same callback may be retried.

## Errors

- `RublexConfigError` — missing API key / bad configuration.
- `RublexRequestError` — network failure or non-JSON response (has `.status`, `.body`).

HTTP-level errors (4xx/5xx) are **not** raised — the parsed envelope is returned so you can inspect `status == "ERROR"` and `message`.

## Building & publishing

```bash
python -m pip install --upgrade build twine
python -m build              # produces dist/*.whl and dist/*.tar.gz
python -m twine upload dist/*
```

## License

MIT © Rublex Team. See [LICENSE.md](LICENSE.md).
