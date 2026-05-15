"""Python client for the Rublex Payment Gateway Merchant API.

(c) Rublex Team <payments@rublex.io>
"""
import os
from urllib.parse import quote

import requests

from .exceptions import RublexConfigError, RublexRequestError
from .invoice_builder import InvoiceBuilder

DEFAULT_BASE_URL = "https://api.pay.rublex.io/terminals/v1/"


class RublexPayments:
    """Client for the Rublex Payment Gateway Merchant API.

    Every method returns the gateway's shared response envelope as a ``dict``::

        {"status": "SUCCESS" | "ERROR", "message": str, "data": Any}

    HTTP-level errors (4xx/5xx) are **not** raised -- the parsed envelope is
    returned so you can inspect ``status`` and ``message``. Network failures
    and non-JSON responses raise :class:`RublexRequestError`.

    Parameters
    ----------
    api_key : str, optional
        60-char terminal token. Falls back to ``RUBLEX_PAYMENTS_API_KEY``.
    base_url : str, optional
        API base URL (including ``/terminals/v1``). Falls back to
        ``RUBLEX_PAYMENTS_URL`` and then to the production URL.
    callback_url : str, optional
        Default ``callback_url`` applied to every invoice you create.
        Falls back to ``RUBLEX_PAYMENTS_CALLBACK_URL``.
    timeout : int, optional
        Per-request timeout in seconds (default 30).
    """

    def __init__(self, api_key=None, base_url=None, callback_url=None, timeout=30):
        api_key = api_key or os.environ.get("RUBLEX_PAYMENTS_API_KEY")
        if not api_key:
            raise RublexConfigError("Rublex API key (terminal token) is not set.")

        self.api_key = api_key
        self.base_url = (
            (base_url or os.environ.get("RUBLEX_PAYMENTS_URL") or DEFAULT_BASE_URL)
            .rstrip("/")
            + "/"
        )
        self.callback_url = callback_url or os.environ.get(
            "RUBLEX_PAYMENTS_CALLBACK_URL"
        )
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {"Accept": "application/json", "Token": self.api_key}
        )
        self._public_session = requests.Session()
        self._public_session.headers.update({"Accept": "application/json"})

    @classmethod
    def from_env(cls):
        """Build a client purely from ``RUBLEX_PAYMENTS_*`` environment variables."""
        return cls()

    # ------------------------------------------------------------------
    # Invoice creation
    # ------------------------------------------------------------------

    def crypto(self):
        """Start a fluent crypto invoice: ``client.crypto().amount(0.5).pick(3)...``"""
        return InvoiceBuilder(self, InvoiceBuilder.TYPE_CRYPTO)

    def fiat(self):
        """Start a fluent fiat invoice: ``client.fiat().amount(19.99).pick(4)...``"""
        return InvoiceBuilder(self, InvoiceBuilder.TYPE_FIAT)

    def create_crypto_invoice(self, data, payer_choice=False):
        """Create a crypto invoice -> ``POST /pay-request``.

        ``data["currency_id"]`` MUST come from a prior call to
        :meth:`get_supported_currencies`. The terminal rejects any id it has
        not enabled with HTTP 422.

        ``payer_choice`` is kept for backwards compatibility and silently
        ignored: the merchant-fixed flow is the only crypto flow exposed today.
        """
        payload = {"callback_url": self.callback_url}
        payload.update(data)
        return self._request("pay-request", "POST", payload)

    def create_fiat_invoice(self, data, payer_choice=False):
        """Create a fiat invoice.

        ``payer_choice=False`` -> ``POST /fiat/pay-request-direct``    (merchant locks gateway)
        ``payer_choice=True``  -> ``POST /fiat/pay-request-selection`` (payer picks gateway)
        """
        payload = {"callback_url": self.callback_url}
        payload.update(data)
        payload["invoice_type"] = (
            "gateway_selection" if payer_choice else "direct_gateway"
        )
        endpoint = (
            "fiat/pay-request-selection"
            if payer_choice
            else "fiat/pay-request-direct"
        )
        return self._request(endpoint, "POST", payload)

    # ------------------------------------------------------------------
    # Terminal & catalog (read-only)
    # ------------------------------------------------------------------

    def get_information(self):
        """``GET /terminals/v1/info``"""
        return self._request("info", "GET")

    def get_currencies(self, page=None, per_page=None):
        """``GET /terminals/v1/currencies``"""
        return self._request("currencies", "GET", {"page": page, "per_page": per_page})

    def get_supported_currencies(self, page=None, per_page=None):
        """``GET /terminals/v1/currencies/supported``"""
        return self._request(
            "currencies/supported", "GET", {"page": page, "per_page": per_page}
        )

    def get_fiat_gateways(self):
        """``GET /terminals/v1/fiat/gateways``"""
        return self._request("fiat/gateways", "GET")

    def get_fiat_currencies(self):
        """``GET /terminals/v1/fiat/currencies``"""
        return self._request("fiat/currencies", "GET")

    # ------------------------------------------------------------------
    # Invoice lookup (read-only)
    # ------------------------------------------------------------------

    def get_crypto_invoice(self, invoice_number):
        """``GET /terminals/v1/invoices?invoice_number=...``"""
        return self._request("invoices", "GET", {"invoice_number": invoice_number})

    def list_crypto_invoices(self, params=None):
        """``GET /terminals/v1/invoices``"""
        return self._request("invoices", "GET", params or {})

    def list_pay_requests(self, params=None):
        """``GET /terminals/v1/pay-requests``"""
        return self._request("pay-requests", "GET", params or {})

    def get_fiat_invoice(self, invoice_number):
        """``GET /terminals/v1/fiat/invoices?invoice_number=...``"""
        return self._request(
            "fiat/invoices", "GET", {"invoice_number": invoice_number}
        )

    def list_fiat_invoices(self, params=None):
        """``GET /terminals/v1/fiat/invoices``"""
        return self._request("fiat/invoices", "GET", params or {})

    # ------------------------------------------------------------------
    # Payer-facing actions on hosted invoices (no Token header)
    # ------------------------------------------------------------------

    def list_fiat_invoice_gateways(self, invoice_number):
        """``GET /terminals/v1/fiat/invoices/{invoice_number}/gateways``"""
        return self._request(
            "fiat/invoices/{}/gateways".format(quote(invoice_number, safe="")),
            "GET",
            public=True,
        )

    def select_fiat_gateway(self, invoice_number, data):
        """``POST /terminals/v1/fiat/invoices/{invoice_number}/select-gateway``"""
        return self._request(
            "fiat/invoices/{}/select-gateway".format(quote(invoice_number, safe="")),
            "POST",
            data,
            public=True,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _request(self, relative_url, method, payload=None, public=False, query=None):
        method = method.upper()
        session = self._public_session if public else self._session
        url = self.base_url + relative_url
        payload = _filter_none(payload or {})

        kwargs = {"timeout": self.timeout}
        if method == "GET":
            kwargs["params"] = payload
        else:
            kwargs["json"] = payload
            if query:
                kwargs["params"] = _filter_none(query)

        try:
            response = session.request(method, url, **kwargs)
        except requests.RequestException as exc:
            raise RublexRequestError(
                'Rublex request to "{}" failed: {}'.format(relative_url, exc)
            ) from exc

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise RublexRequestError(
                'Rublex returned a non-JSON response from "{}".'.format(relative_url),
                status=response.status_code,
                body=response.text,
            ) from exc


def _filter_none(data):
    return {k: v for k, v in data.items() if v is not None}
