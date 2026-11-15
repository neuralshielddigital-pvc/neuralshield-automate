"""Exact allowlist for the separate Whop recurring Workflow Automation SaaS.

The existing AGENCY_WHOP_PRODUCT_* mapping is for *one-time* digital goods;
never reuse that configuration to grant monthly SaaS access.
"""
from __future__ import annotations

from app.core.config import settings
from app.services.agency_saas_whop_guardrails import RecurringPlan


def configured_recurring_saas_plans() -> dict[str, RecurringPlan]:
    """Return strict plan-ID-to-contract mapping or fail closed.

    No default live IDs, no silent fallback to Paddle or Agency products, and
    no automatic enablement. An operator must separately provision approved
    recurring plan/product pairs before enabling the lifecycle.
    """
    if not settings.AGENCY_SAAS_WHOP_ENABLED:
        return {}
    if not settings.AGENCY_WHOP_ACCOUNT_ID.startswith("biz_"):
        raise ValueError("Recurring Whop SaaS merchant is not configured")
    definitions = (
        ("starter", settings.AGENCY_SAAS_WHOP_STARTER_PRODUCT_ID,
         settings.AGENCY_SAAS_WHOP_STARTER_PLAN_ID, 1900),
        ("pro", settings.AGENCY_SAAS_WHOP_PRO_PRODUCT_ID,
         settings.AGENCY_SAAS_WHOP_PRO_PLAN_ID, 5900),
        ("business", settings.AGENCY_SAAS_WHOP_BUSINESS_PRODUCT_ID,
         settings.AGENCY_SAAS_WHOP_BUSINESS_PLAN_ID, 14900),
    )
    products: set[str] = set()
    plan_ids: set[str] = set()
    plans: dict[str, RecurringPlan] = {}
    for tier, product_id, plan_id, cents in definitions:
        # No whitespaces, empty or generic IDs, or accidental one-time plan IDs.
        if (
            not isinstance(product_id, str) or not product_id.startswith("prod_")
            or product_id != product_id.strip()
            or not isinstance(plan_id, str) or not plan_id.startswith("plan_")
            or plan_id != plan_id.strip()
            or len(product_id) < 9 or len(plan_id) < 9
        ):
            raise ValueError(f"Invalid recurring Whop SaaS IDs for {tier}")
        if product_id in products or plan_id in plan_ids:
            raise ValueError("Duplicate recurring Whop SaaS product/plan ID")
        products.add(product_id)
        plan_ids.add(plan_id)
        plans[plan_id] = RecurringPlan(
            product_id=product_id, checkout_plan_id=plan_id,
            tier=tier, monthly_usd_cents=cents,
        )
    one_time_products = {
        settings.AGENCY_WHOP_PRODUCT_STARTER_ID,
        settings.AGENCY_WHOP_PRODUCT_PRO_ID,
        settings.AGENCY_WHOP_PRODUCT_ADVANCED_ID,
        settings.AGENCY_WHOP_PRODUCT_LICENSE_ID,
    } - {""}
    if products & one_time_products:
        raise ValueError("Recurring SaaS product overlaps one-time Agency commerce")
    return plans
