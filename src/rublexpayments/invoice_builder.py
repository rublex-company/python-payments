"""Fluent builder for invoice creation.

(c) Rublex Team <payments@rublex.io>

Entry points : client.crypto() / client.fiat()
Direction    : pick(id)    -> merchant locks the coin/gateway
               by_payer()  -> fiat only: payer picks gateway on the hosted page
Rate (fiat)  : lock_rate() / lock_rate(False)
Customer     : customer(email=..., first_name=...)
Return URLs  : success(url) / failed(url) / return_to(url)
Execute      : create_invoice(**extras)

Crypto pre-flight (NON-OPTIONAL): the ``currency_id`` you pass to pick() MUST
come from a fresh call to ``client.get_supported_currencies()``. The terminal
rejects any id it has not enabled with HTTP 422.
"""

TYPE_CRYPTO = "crypto"
TYPE_FIAT = "fiat"


class InvoiceBuilder:
    """Fluent builder for crypto/fiat invoice creation."""

    TYPE_CRYPTO = TYPE_CRYPTO
    TYPE_FIAT = TYPE_FIAT

    def __init__(self, client, type_):
        self._client = client
        self._type = type_
        self._payer_choice = False
        self._data = {}

        if type_ == TYPE_FIAT:
            self._data["fixed_rate"] = True

    def amount(self, amount):
        self._data["amount"] = amount
        return self

    def pick(self, id_):
        """Pick the coin (crypto) or gateway (fiat) this invoice locks to.

        Still meaningful in by_payer() mode: for crypto it is the payout coin,
        for fiat it is the default gateway suggestion.
        """
        key = "currency_id" if self._type == TYPE_CRYPTO else "gateway_id"
        self._data[key] = id_
        return self

    def by_payer(self):
        """Fiat only: hand the gateway choice to the payer on the hosted page.

        Has no effect for crypto invoices -- the merchant always picks the coin.
        """
        self._payer_choice = True
        return self

    def callback(self, url):
        self._data["callback_url"] = url
        return self

    def success(self, url):
        """Where the hosted page sends the payer after a successful payment."""
        self._data["success_url"] = url
        return self

    def failed(self, url):
        """Where the hosted page sends the payer after a failed/cancelled/expired payment."""
        self._data["failed_url"] = url
        return self

    def return_to(self, url):
        """Shortcut: same URL for both success and failure (recommended)."""
        return self.success(url).failed(url)

    def lock_rate(self, lock=True):
        """Fiat-only: control the FX rate behaviour.

        ``lock_rate()``       -> lock the rate at invoice creation time
        ``lock_rate(False)``  -> let the rate float until the payer pays
        """
        self._data["fixed_rate"] = lock
        return self

    def customer(self, email=None, first_name=None, last_name=None, mobile=None):
        """Fiat-only: pre-fill payer details. All fields optional."""
        if email is not None:
            self._data["customer_email"] = email
        if first_name is not None:
            self._data["customer_first_name"] = first_name
        if last_name is not None:
            self._data["customer_last_name"] = last_name
        if mobile is not None:
            self._data["customer_mobile"] = mobile
        return self

    def create_invoice(self, **extras):
        """Send the request and return the ``{status, message, data}`` envelope."""
        data = dict(self._data)
        data.update(extras)

        if self._type == TYPE_CRYPTO:
            return self._client.create_crypto_invoice(data)
        return self._client.create_fiat_invoice(data, self._payer_choice)
