from types import SimpleNamespace

import pytest

from app.services import agency_whop_settings


def test_whop_is_off_by_default(monkeypatch):
    monkeypatch.setattr(agency_whop_settings, "settings", SimpleNamespace(AGENCY_WHOP_ENABLED=False))
    assert agency_whop_settings.configured_agency_whop_products() == {}


def test_whop_enabled_requires_complete_secrets_and_unique_products(monkeypatch):
    base = dict(
        AGENCY_WHOP_ENABLED=True,
        AGENCY_WHOP_API_KEY="test-only",
        AGENCY_WHOP_WEBHOOK_SECRET="test-only",
        AGENCY_WHOP_PRODUCT_STARTER_ID="p1",
        AGENCY_WHOP_PRODUCT_PRO_ID="p2",
        AGENCY_WHOP_PRODUCT_ADVANCED_ID="p3",
        AGENCY_WHOP_PRODUCT_LICENSE_ID="p4",
    )
    monkeypatch.setattr(agency_whop_settings, "settings", SimpleNamespace(**base))
    assert agency_whop_settings.configured_agency_whop_products()["p1"] == "starter-toolkit"
    for change in (
        {"AGENCY_WHOP_API_KEY": ""},
        {"AGENCY_WHOP_WEBHOOK_SECRET": ""},
        {"AGENCY_WHOP_PRODUCT_PRO_ID": ""},
        {"AGENCY_WHOP_PRODUCT_LICENSE_ID": "p1"},
    ):
        monkeypatch.setattr(agency_whop_settings, "settings", SimpleNamespace(**{**base, **change}))
        with pytest.raises(ValueError):
            agency_whop_settings.configured_agency_whop_products()
