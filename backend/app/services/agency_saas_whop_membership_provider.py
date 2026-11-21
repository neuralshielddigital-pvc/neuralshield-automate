"""Read-only Whop membership adapter (current API, 2026-11-14-1).

Official contract: https://docs.whop.com/api-reference/memberships/retrieve-membership
No webhook/browser facts are trusted. A verified membership alone NEVER grants
paid access; payment-backed reconciliation is a separate mandatory gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re

from app.services.agency_whop_provider import WhopProvider
from app.services.agency_saas_whop_guardrails import VerifiedSubscriptionFacts


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous provider facts, including nested duplicate JSON keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate membership JSON field")
        result[key] = value
    return result


def _reject_nonfinite(value: str):
    raise ValueError("Non-finite membership JSON value")


def _cents(value: object) -> int:
    if not isinstance(value, dict) or value.get("currency") != "usd":
        raise ValueError("Invalid Whop renewal currency")
    raw = value.get("amount")
    if not isinstance(raw, str):
        raise ValueError("Invalid Whop renewal amount")
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid Whop renewal amount") from exc
    if not number.is_finite() or number <= 0 or number.as_tuple().exponent < -2:
        raise ValueError("Invalid Whop renewal amount")
    return int(number * 100)


class WhopMembershipProvider:
    """Normalize authenticated merchant-owned memberships, never raw events."""

    def __init__(self, *, api_key: str, merchant_id: str):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Whop server credential required")
        if not isinstance(merchant_id, str) or not re.fullmatch(r"biz_[A-Za-z0-9_-]{1,128}", merchant_id):
            raise ValueError("Whop merchant required")
        self._client = WhopProvider(api_key, merchant_id)
        self._merchant_id = merchant_id

    def retrieve_verified_subscription(self, subscription_id: str) -> VerifiedSubscriptionFacts:
        if not isinstance(subscription_id, str) or not re.fullmatch(r"mem_[A-Za-z0-9_-]{1,128}", subscription_id):
            raise ValueError("Invalid membership identifier")
        # The existing authenticated GET helper is intentionally restricted to
        # one-time resources; membership retrieval is added as a separate
        # read-only endpoint without changing its existing purchase behavior.
        import requests
        from app.services.agency_whop_provider import WhopUnavailable
        try:
            response = requests.get(
                f"https://api.whop.com/api/v1/memberships/{subscription_id}",
                headers={"Authorization": f"Bearer {self._client.key}",
                         "Api-Version-Date": "2026-11-14-1"},
                timeout=(2, 3), allow_redirects=False,
            )
            if response.status_code != 200 or len(response.content) > 262144:
                raise WhopUnavailable("Membership lookup failed")
            record = json.loads(\n                response.content, object_pairs_hook=_unique_json_object,\n                parse_constant=_reject_nonfinite,\n            )
        except (requests.RequestException, ValueError) as exc:
            raise WhopUnavailable("Membership lookup failed") from exc
        if not isinstance(record, dict) or record.get("id") != subscription_id:
            raise ValueError("Membership identity mismatch")
        account = record.get("account")
        if not isinstance(account, dict) or account.get("id") != self._merchant_id:
            raise ValueError("Membership merchant mismatch")
        customer_id = record.get("user_id")
        if not isinstance(customer_id, str) or not re.fullmatch(r"user_[A-Za-z0-9_-]{1,128}", customer_id):
            raise ValueError("Membership has no claimed user")
        updated = record.get("updated_at")
        if not isinstance(updated, str):
            raise ValueError("Membership timestamp missing")
        try:
            observed = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Membership timestamp invalid") from exc
        if observed.tzinfo is None or observed > datetime.now(timezone.utc):
            raise ValueError("Membership timestamp invalid")
        if record.get("billing_period_days") not in (28, 29, 30, 31):
            raise ValueError("Membership is not verified monthly")
        if record.get("cancel_at_period_end") is True:
            # Do not silently treat scheduled cancellation as renewable access.
            status = "canceled"
        else:
            status = record.get("status")
        if not isinstance(status, str):
            raise ValueError("Membership status missing")
        return VerifiedSubscriptionFacts(
            merchant_id=self._merchant_id, product_id=record.get("product_id"),
            checkout_plan_id=record.get("variant_id"), subscription_id=subscription_id,
            customer_id=customer_id, provider_status=status,
            amount_usd_cents=_cents(record.get("renewal_price")),
            currency="USD", billing_interval="month", observed_at=observed,
        )
