"""Synthetic contract checks for read-only Whop membership adapter."""
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from app.services.agency_saas_whop_membership_provider import WhopMembershipProvider, _cents
from app.services.agency_whop_provider import WhopUnavailable


MERCHANT = "biz_testMerchant"
MEMBER = "mem_testMember"


def provider():
    return WhopMembershipProvider(api_key="test-server-key", merchant_id=MERCHANT)


def record(**overrides):
    base = {
        "id": MEMBER, "account": {"id": MERCHANT}, "user_id": "user_testBuyer",
        "product_id": "prod_testProduct", "variant_id": "plan_testPlan",
        "status": "active", "billing_period_days": 30,
        "cancel_at_period_end": False,
        "renewal_price": {"amount": "19.00", "currency": "usd"},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def response(payload):
    import json
    return Mock(status_code=200, content=json.dumps(payload).encode())


def test_authenticated_membership_normalizes_without_entitlement_write():
    with patch("requests.get", return_value=response(record())) as get:
        facts = provider().retrieve_verified_subscription(MEMBER)
    assert facts.subscription_id == MEMBER
    assert facts.customer_id == "user_testBuyer"
    assert facts.amount_usd_cents == 1900
    assert get.call_args.kwargs["allow_redirects"] is False
    assert get.call_args.kwargs["headers"]["Api-Version-Date"] == "2026-11-14-1"


@pytest.mark.parametrize("changes", [
    {"id": "mem_other"}, {"account": {"id": "biz_other"}},
    {"user_id": None}, {"billing_period_days": None},
    {"renewal_price": {"amount": "0.00", "currency": "usd"}},
    {"renewal_price": {"amount": "19.00", "currency": "eur"}},
    {"updated_at": "not-a-date"},
])
def test_malformed_or_foreign_membership_rejected(changes):
    with patch("requests.get", return_value=response(record(**changes))):
        with pytest.raises(ValueError):
            provider().retrieve_verified_subscription(MEMBER)


def test_invalid_id_does_not_call_whop():
    with patch("requests.get") as get:
        with pytest.raises(ValueError):
            provider().retrieve_verified_subscription("https://attacker.invalid")
    get.assert_not_called()


@pytest.mark.parametrize("value", ["19.001", "-1", "NaN", "Infinity", "abc"])
def test_unsafe_money_rejected(value):
    with pytest.raises(ValueError):
        _cents({"amount": value, "currency": "usd"})


@pytest.mark.parametrize("raw", [
    b'{"id":"mem_testMember","id":"mem_other"}',
    b'{"id":"mem_testMember","account":{"id":"biz_testMerchant","id":"biz_other"}}',
    b'{"id":"mem_testMember","renewal_price":{"amount":"19.00","amount":"149.00"}}',
    b'{"id":"mem_testMember","renewal_price":{"amount":NaN}}',
    b'{"id":"mem_testMember","renewal_price":{"amount":Infinity}}',
])
def test_ambiguous_provider_json_never_normalizes(raw):
    with patch("requests.get", return_value=Mock(status_code=200, content=raw)):
        with pytest.raises(WhopUnavailable):
            provider().retrieve_verified_subscription(MEMBER)


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404, 429, 500, 503])
def test_membership_http_failure_is_fail_closed(status):
    with patch("requests.get", return_value=Mock(status_code=status, content=b"{}")):
        with pytest.raises(WhopUnavailable):
            provider().retrieve_verified_subscription(MEMBER)


def test_oversized_membership_response_is_fail_closed():
    with patch("requests.get", return_value=Mock(status_code=200, content=b"x" * 262145)):
        with pytest.raises(WhopUnavailable):
            provider().retrieve_verified_subscription(MEMBER)


def test_membership_transport_timeout_is_fail_closed():
    import requests
    with patch("requests.get", side_effect=requests.Timeout("synthetic timeout")):
        with pytest.raises(WhopUnavailable):
            provider().retrieve_verified_subscription(MEMBER)


def test_membership_request_is_bounded_and_uses_server_authentication():
    with patch("requests.get", return_value=response(record())) as get:
        provider().retrieve_verified_subscription(MEMBER)
    args, kwargs = get.call_args
    assert args == (f"https://api.whop.com/api/v1/memberships/{MEMBER}",)
    assert kwargs["timeout"] == (2, 3)
    assert kwargs["allow_redirects"] is False
    assert kwargs["headers"]["Authorization"] == "Bearer test-server-key"


@pytest.mark.parametrize("value", [
    "1e1000000", "9" * 10000, "000000000", "19.000",
    "+19.00", " 19.00", "19.00 ", "1E2",
])
def test_renewal_amount_rejects_unbounded_or_noncanonical_numbers(value):
    with pytest.raises(ValueError, match="Invalid Whop renewal amount"):
        _cents({"amount": value, "currency": "usd"})
