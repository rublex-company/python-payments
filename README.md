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
