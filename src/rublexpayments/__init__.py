"""Python SDK for the Rublex Payment Gateway.

(c) Rublex Team <payments@rublex.io>

Wraps every endpoint of the Rublex Merchant API with a thin client, plus a
fluent invoice builder. Mirrors the Laravel SDK (``rublex/laravel-payments``)
and the Node SDK (``@rublex/payments``).

PyPI name: ``rublexpayments``. Import name: ``rublexpayments``.
"""

from .client import RublexPayments
from .invoice_builder import InvoiceBuilder
from .exceptions import (
    RublexError,
    RublexConfigError,
    RublexRequestError,
)

__version__ = "1.2.0"
__all__ = [
    "RublexPayments",
    "InvoiceBuilder",
    "RublexError",
    "RublexConfigError",
    "RublexRequestError",
    "__version__",
]
