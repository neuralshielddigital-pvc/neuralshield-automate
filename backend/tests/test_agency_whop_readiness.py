from types import SimpleNamespace

from app.services import agency_whop_readiness


def test_readiness_reports_missing_configuration_and_never_claims_live_ready(monkeypatch):
    config = dict(
        AGENCY_WHOP_API_KEY="", AGENCY_WHOP_WEBHOOK_SECRET="",
        AGENCY_WHOP_PRODUCT_STARTER_ID="", AGENCY_WHOP_PRODUCT_PRO_ID="",
        AGENCY_WHOP_PRODUCT_ADVANCED_ID="", AGENCY_WHOP_PRODUCT_LICENSE_ID="",
    )
    monkeypatch.setattr(agency_whop_readiness, "settings", SimpleNamespace(**config))
    result = agency_whop_readiness.inspect_agency_whop_readiness()
    assert not result.ready_for_provider_contract_review
    assert not result.ready_for_live_activation
    assert "missing_api_key" in result.blockers
    assert "missing_or_duplicate_product_ids" in result.blockers


def test_even_configured_whop_must_pass_real_provider_integration(monkeypatch):
    config = dict(
        AGENCY_WHOP_API_KEY="synthetic", AGENCY_WHOP_WEBHOOK_SECRET="synthetic",
        AGENCY_WHOP_PRODUCT_STARTER_ID="a", AGENCY_WHOP_PRODUCT_PRO_ID="b",
        AGENCY_WHOP_PRODUCT_ADVANCED_ID="c", AGENCY_WHOP_PRODUCT_LICENSE_ID="d",
    )
    monkeypatch.setattr(agency_whop_readiness, "settings", SimpleNamespace(**config))
    result = agency_whop_readiness.inspect_agency_whop_readiness()
    assert result.ready_for_provider_contract_review
    assert not result.ready_for_live_activation
    assert "official_webhook_signature_adapter_unverified" in result.blockers
