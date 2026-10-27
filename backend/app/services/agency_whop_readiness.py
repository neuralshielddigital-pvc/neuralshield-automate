"""Read-only Agency Whop rollout readiness inspection.

No provider calls, secrets, database writes, feature activation or deployment.
"""
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class AgencyWhopReadiness:
    ready_for_provider_contract_review: bool
    ready_for_live_activation: bool
    blockers: tuple[str, ...]


def inspect_agency_whop_readiness() -> AgencyWhopReadiness:
    blockers = []
    if not settings.AGENCY_WHOP_API_KEY.strip():
        blockers.append("missing_api_key")
    if not settings.AGENCY_WHOP_WEBHOOK_SECRET.strip():
        blockers.append("missing_webhook_secret")
    products = (
        settings.AGENCY_WHOP_PRODUCT_STARTER_ID,
        settings.AGENCY_WHOP_PRODUCT_PRO_ID,
        settings.AGENCY_WHOP_PRODUCT_ADVANCED_ID,
        settings.AGENCY_WHOP_PRODUCT_LICENSE_ID,
    )
    if any(not item.strip() for item in products) or len(set(products)) != 4:
        blockers.append("missing_or_duplicate_product_ids")
    # Official Whop signature format/API response contract and real checkout
    # have not been verified. This deliberately cannot certify live readiness.
    blockers.extend((
        "official_webhook_signature_adapter_unverified",
        "authenticated_whop_purchase_api_adapter_unverified",
        "end_to_end_live_payment_validation_pending",
    ))
    return AgencyWhopReadiness(
        ready_for_provider_contract_review=not any(
            b in blockers for b in (
                "missing_api_key", "missing_webhook_secret",
                "missing_or_duplicate_product_ids",
            )
        ),
        ready_for_live_activation=False,
        blockers=tuple(blockers),
    )
