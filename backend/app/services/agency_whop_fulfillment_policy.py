"""Pure, fail-closed decision for Agency Whop fulfillment.

Input must be produced from authenticated server-to-server payment lookup, not
browser redirects or unverified webhook JSON. No database writes occur here.
"""
from dataclasses import dataclass
from typing import Literal

from app.services.agency_whop_contract import VerifiedAgencyPurchase


@dataclass(frozen=True)
class FulfillmentDecision:
    action: Literal["grant", "duplicate", "reject"]
    reason: str


def decide_whop_fulfillment(
    purchase: VerifiedAgencyPurchase,
    *,
    existing_order_provider: str | None,
    existing_order_id: str | None,
    existing_order_product_key: str | None,
    payment_reversed: bool = False,
) -> FulfillmentDecision:
    if purchase.provider != "whop":
        return FulfillmentDecision("reject", "wrong_provider")
    if payment_reversed:
        return FulfillmentDecision("reject", "payment_reversed")
    if not purchase.provider_order_id:
        return FulfillmentDecision("reject", "missing_order_id")
    if existing_order_provider is None and existing_order_id is None:
        return FulfillmentDecision("grant", "new_verified_order")
    if (
        existing_order_provider == "whop"
        and existing_order_id == purchase.provider_order_id
        and existing_order_product_key == purchase.product_key
    ):
        return FulfillmentDecision("duplicate", "already_recorded")
    return FulfillmentDecision("reject", "provider_order_conflict")
