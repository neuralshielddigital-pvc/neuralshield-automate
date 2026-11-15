"""Fail-closed recurring Whop SaaS plan configuration tests; no network calls."""
from types import SimpleNamespace

import pytest

from app.services import agency_saas_whop_settings as module


def make_settings(**changes):
    defaults = dict(
        AGENCY_SAAS_WHOP_ENABLED=True,
        AGENCY_WHOP_ACCOUNT_ID="biz_example_recurring",
        AGENCY_SAAS_WHOP_STARTER_PRODUCT_ID="prod_monthly_starter",
        AGENCY_SAAS_WHOP_STARTER_PLAN_ID="plan_monthly_starter",
        AGENCY_SAAS_WHOP_PRO_PRODUCT_ID="prod_monthly_pro",
        AGENCY_SAAS_WHOP_PRO_PLAN_ID="plan_monthly_pro",
        AGENCY_SAAS_WHOP_BUSINESS_PRODUCT_ID="prod_monthly_business",
        AGENCY_SAAS_WHOP_BUSINESS_PLAN_ID="plan_monthly_business",
        AGENCY_WHOP_PRODUCT_STARTER_ID="prod_onetime_starter",
        AGENCY_WHOP_PRODUCT_PRO_ID="prod_onetime_pro",
        AGENCY_WHOP_PRODUCT_ADVANCED_ID="prod_onetime_advanced",
        AGENCY_WHOP_PRODUCT_LICENSE_ID="prod_onetime_license",
    )
    defaults.update(changes)
    return SimpleNamespace(**defaults)


def test_disabled_is_empty_and_cannot_grant(monkeypatch):
    monkeypatch.setattr(module, "settings", make_settings(AGENCY_SAAS_WHOP_ENABLED=False))
    assert module.configured_recurring_saas_plans() == {}


def test_approved_three_monthly_tiers_have_exact_price_contracts(monkeypatch):
    monkeypatch.setattr(module, "settings", make_settings())
    result = module.configured_recurring_saas_plans()
    assert sorted(result) == ["plan_monthly_business", "plan_monthly_pro", "plan_monthly_starter"]
    assert {x.tier: x.monthly_usd_cents for x in result.values()} == {
        "starter": 1900, "pro": 5900, "business": 14900,
    }
    assert all(key == value.checkout_plan_id for key, value in result.items())


@pytest.mark.parametrize("overrides", [
    {"AGENCY_WHOP_ACCOUNT_ID": "biz_wrong", "AGENCY_SAAS_WHOP_STARTER_PLAN_ID": ""},
    {"AGENCY_WHOP_ACCOUNT_ID": ""},
    {"AGENCY_SAAS_WHOP_STARTER_PLAN_ID": ""},
    {"AGENCY_SAAS_WHOP_STARTER_PLAN_ID": "plan_"},
    {"AGENCY_SAAS_WHOP_PRO_PLAN_ID": "plan_monthly_starter"},
    {"AGENCY_SAAS_WHOP_BUSINESS_PRODUCT_ID": "prod_monthly_pro"},
    {"AGENCY_SAAS_WHOP_PRO_PRODUCT_ID": "product_invalid"},
    {"AGENCY_SAAS_WHOP_PRO_PLAN_ID": " plan_monthly_pro "},
    {"AGENCY_SAAS_WHOP_PRO_PRODUCT_ID": "prod_onetime_pro"},
])
def test_invalid_or_colliding_configuration_never_returns_allowlist(monkeypatch, overrides):
    monkeypatch.setattr(module, "settings", make_settings(**overrides))
    with pytest.raises(ValueError):
        module.configured_recurring_saas_plans()


def test_old_onetime_products_do_not_match_monthly_plans(monkeypatch):
    monkeypatch.setattr(module, "settings", make_settings())
    result = module.configured_recurring_saas_plans()
    assert all(
        item.product_id not in {
            "prod_onetime_starter", "prod_onetime_pro",
            "prod_onetime_advanced", "prod_onetime_license",
        } for item in result.values()
    )
