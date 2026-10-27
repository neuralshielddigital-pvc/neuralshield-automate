"""Non-activated orchestration boundary for Agency Whop purchases.

Only an authenticated provider lookup may supply purchase facts. This module
has no HTTP endpoint and no production routing. Webhook authenticity must be
verified by a future adapter before invoking this boundary.
"""
from app.services.agency_whop_purchase_lookup import (
    AuthenticatedWhopPurchaseLookup, prepare_verified_whop_purchase,
)
from app.services.agency_whop_persistence import AgencyWhopPersistence


def reconcile_authenticated_whop_purchase(
    *,
    order_id: str,
    lookup: AuthenticatedWhopPurchaseLookup,
    product_map: dict[str, str],
    persistence: AgencyWhopPersistence,
    webhook_authenticated: bool,
) -> dict:
    if webhook_authenticated is not True:
        raise ValueError("Authenticated Whop webhook required")
    if not product_map:
        raise ValueError("Whop product configuration unavailable")
    verified = prepare_verified_whop_purchase(
        order_id=order_id,
        lookup=lookup,
        product_map=product_map,
    )
    return persistence.record_verified_purchase(verified)
