"""Smoke tests — no network calls."""
import pytest

from rublexpayments import (
    RublexPayments,
    InvoiceBuilder,
    RublexConfigError,
)

TOKEN = "x" * 60


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("RUBLEX_PAYMENTS_API_KEY", raising=False)
    with pytest.raises(RublexConfigError):
        RublexPayments()


def test_crypto_builder_payload():
    client = RublexPayments(api_key=TOKEN)
    builder = client.crypto().amount(0.5).pick(3)
    assert isinstance(builder, InvoiceBuilder)
    assert builder._data["amount"] == 0.5
    assert builder._data["currency_id"] == 3
    assert builder._payer_choice is False


def test_by_payer_flags_fiat_gateway_selection():
    client = RublexPayments(api_key=TOKEN)
    builder = client.fiat().amount(50).by_payer()
    assert builder._payer_choice is True


def test_return_to_sets_both_success_and_failed_urls():
    client = RublexPayments(api_key=TOKEN)
    builder = (
        client.crypto()
        .amount(0.5)
        .pick(3)
        .return_to("https://example.com/return")
    )
    assert builder._data["success_url"] == "https://example.com/return"
    assert builder._data["failed_url"] == "https://example.com/return"


def test_fiat_builder_defaults_fixed_rate_to_true():
    client = RublexPayments(api_key=TOKEN)
    builder = client.fiat().amount(19.99).pick(4)
    assert builder._data["fixed_rate"] is True
    assert builder._data["gateway_id"] == 4


def test_customer_maps_to_snake_case():
    client = RublexPayments(api_key=TOKEN)
    builder = (
        client.fiat()
        .amount(1)
        .customer(email="a@b.com", first_name="Ada", last_name="L", mobile="+1")
    )
    assert builder._data["customer_email"] == "a@b.com"
    assert builder._data["customer_first_name"] == "Ada"
    assert builder._data["customer_last_name"] == "L"
    assert builder._data["customer_mobile"] == "+1"


def test_base_url_normalises_trailing_slashes():
    client = RublexPayments(
        api_key=TOKEN,
        base_url="https://api.pay.rublex.io/terminals/v1///",
    )
    assert client.base_url == "https://api.pay.rublex.io/terminals/v1/"


def test_from_env_reads_api_key(monkeypatch):
    monkeypatch.setenv("RUBLEX_PAYMENTS_API_KEY", TOKEN)
    monkeypatch.setenv("RUBLEX_PAYMENTS_CALLBACK_URL", "https://example.com/cb")
    client = RublexPayments.from_env()
    assert client.api_key == TOKEN
    assert client.callback_url == "https://example.com/cb"
