"""Gate Whop fulfillment behind independently authenticated provider verification.

No webhook payload or browser return is trusted. The actual Whop API adapter
must be implemented separately against its verified contract; this module
cannot issue entitlements or mutate the database.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.agency_whop_contract import (
    VerifiedAgencyPurchase,
    validate_verified_whop_purchase,
)


@dataclass(frozen=True)
class ProviderPurchaseFacts:
    order_id: str
    product_id: str
    status: str
    amount_usd: str
    currency: str
    customer_email: str


class AuthenticatedWhopPurchaseLookup(Protocol):
    """Implementations must authenticate the provider response server-side."""

    def fetch_authenticated_purchase(self, order_id: str) -> ProviderPurchaseFacts:
        ...


def prepare_verified_whop_purchase(
    *,
    order_id: str,
    lookup: AuthenticatedWhopPurchaseLookup,
    product_map: dict[str, str],
) -> VerifiedAgencyPurchase:
    if not isinstance(order_id, str) or not order_id.strip() or len(order_id) > 255:
        raise ValueError("Invalid purchase lookup identifier")
    facts = lookup.fetch_authenticated_purchase(order_id.strip())
    if not isinstance(facts, ProviderPurchaseFacts):
        raise ValueError("Provider returned invalid purchase facts")
    if facts.order_id != order_id.strip():
        raise ValueError("Provider purchase ID mismatch")
    return validate_verified_whop_purchase(
        independently_verified=True,
        payment_status=facts.status,
        provider_order_id=facts.order_id,
        provider_product_id=facts.product_id,
        configured_product_map=product_map,
        amount=facts.amount_usd,
        currency=facts.currency,
        customer_email=facts.customer_email,
    )
