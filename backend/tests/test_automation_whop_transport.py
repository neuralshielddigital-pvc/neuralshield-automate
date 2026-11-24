import base64
import hashlib
import hmac
import json
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from app.services.automation_whop_contract import CheckoutIntent, CommercialError, Plan, TenantContext
from app.services.automation_whop_transport import (
    API_VERSION_DATE,
    WEBHOOK_API_VERSION_DATE,
    WhopAdapter,
    WhopBinding,
    WhopError,
    WhopSettings,
    WhopUnavailable,
    minor_amount,
    verify_notice,
)


def intent() -> CheckoutIntent:
    return CheckoutIntent(
        "intent-a",
        "tenant-a",
        Plan("fixture-v1", "starter", "USD", "month", 4900, "starter-v1"),
        "fixture-key",
    )


def binding() -> WhopBinding:
    return WhopBinding("fixture-v1", "starter", "prod_test", "plan_test", 4900, "month")


def metadata() -> dict[str, object]:
    return {
        "nsauto_intent_id": "intent-a",
        "nsauto_catalog_version": "fixture-v1",
        "nsauto_tenant_id": "tenant-a",
    }


def resources() -> dict[str, dict[str, object]]:
    price = {"currency": "usd", "amount": "49.00"}
    return {
        "/api/v1/variants/plan_test": {
            "id": "plan_test",
            "account": {"id": "biz_test"},
            "product": {"id": "prod_test"},
            "billing_type": "renewal",
            "currency": "usd",
            "billing_period": 30,
            "initial_price": 0,
            "renewal_price": 49,
            "trial_period_days": None,
        },
        "/api/v1/checkout_configurations": {
            "id": "ch_test",
            "account_id": "biz_test",
            "mode": "payment",
            "metadata": metadata(),
            "variant": {"id": "plan_test"},
            "purchase_url": "https://sandbox.whop.com/checkout/ch_test/",
        },
        "/api/v1/payments/pay_test": {
            "id": "pay_test",
            "account_id": "biz_test",
            "status": "paid",
            "substatus": "succeeded",
            "variant_id": "plan_test",
            "product_id": "prod_test",
            "metadata": metadata(),
            "currency": "usd",
            "membership_id": "mem_test",
            "subtotal": price,
            "total": price,
            "line_items": [
                {
                    "variant_id": "plan_test",
                    "product_id": "prod_test",
                    "quantity": 1,
                    "subtotal": price,
                }
            ],
        },
        "/api/v1/memberships/mem_test": {
            "id": "mem_test",
            "account": {"id": "biz_test"},
            "status": "active",
            "variant_id": "plan_test",
            "product_id": "prod_test",
            "metadata": metadata(),
        },
    }


def adapter(data: dict[str, dict[str, object]], calls: list[httpx.Request]) -> WhopAdapter:
    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=data[request.url.path])

    return WhopAdapter(
        WhopSettings("biz_test", "synthetic-key", enabled=True),
        httpx.Client(transport=httpx.MockTransport(respond)),
    )


def signed_notice(
    *, timestamp: str = "1000", overrides: dict[str, object] | None = None
) -> tuple[bytes, dict[str, str]]:
    payload: dict[str, object] = {
        "id": "msg_test",
        "type": "payment.succeeded",
        "account_id": "biz_test",
        "api_version": "v1",
        "api_version_date": WEBHOOK_API_VERSION_DATE,
        "data": {"id": "pay_test"},
    }
    payload.update(overrides or {})
    raw = json.dumps(payload).encode()
    digest = hmac.new(
        b"ws_synthetic", b"msg_test." + timestamp.encode() + b"." + raw, hashlib.sha256
    ).digest()
    return raw, {
        "webhook-id": "msg_test",
        "webhook-timestamp": timestamp,
        "webhook-signature": "v1," + base64.b64encode(digest).decode(),
    }


def test_disabled_is_default_and_makes_no_network_call() -> None:
    calls: list[httpx.Request] = []
    client = adapter(resources(), calls)
    client.settings = WhopSettings("biz_test", "synthetic-key")
    with pytest.raises(WhopError, match="whop_disabled"):
        client.create_checkout(TenantContext("tenant-a", "actor-a"), intent(), binding())
    assert calls == []
    assert "synthetic-key" not in repr(client.settings)


def test_checkout_is_tenant_bound_before_provider_call() -> None:
    calls: list[httpx.Request] = []
    client = adapter(resources(), calls)
    with pytest.raises(CommercialError, match="tenant_mismatch"):
        client.create_checkout(TenantContext("tenant-b", "actor-b"), intent(), binding())
    with pytest.raises(CommercialError, match="authentication_required"):
        client.create_checkout(TenantContext("tenant-a", "actor-a", False), intent(), binding())
    assert calls == []


def test_checkout_posts_server_metadata_and_fixed_redirect_without_granting() -> None:
    calls: list[httpx.Request] = []
    purchase = intent()
    result = adapter(resources(), calls).create_checkout(
        TenantContext("tenant-a", "actor-a"), purchase, binding()
    )
    assert result.purchase_url == "https://sandbox.whop.com/checkout/ch_test/"
    request = calls[-1]
    payload = json.loads(request.content)
    assert payload["metadata"] == metadata()
    assert payload["variant_id"] == "plan_test"
    assert payload["redirect_url"] == "https://app.neuralshielddigital.com/dashboard/billing"
    # Opaque server workspace routing is persisted provider metadata; it is
    # never an authorization claim and contains no member email or actor ID.
    assert payload["metadata"]["nsauto_tenant_id"] == purchase.tenant_id
    assert "actor-a" not in request.content.decode()
    assert request.headers["Api-Version-Date"] == API_VERSION_DATE
    assert request.url.host == "sandbox-api.whop.com"
    assert purchase.payment_id is None


@pytest.mark.parametrize(
    "url",
    [
        "http://sandbox.whop.com/checkout/ch_test",
        "https://whop.com/checkout/ch_test",
        "https://sandbox.whop.com.evil.test/checkout/ch_test",
        "https://sandbox.whop.com:443/checkout/ch_test",
        "https://sandbox.whop.com/checkout/ch_other",
        "https://sandbox.whop.com/checkout/ch_test?next=evil",
        "https://sandbox.whop.com/checkout/ch_test#bad",
    ],
)
def test_checkout_response_cannot_redirect_to_untrusted_destination(url: str) -> None:
    data = resources()
    data["/api/v1/checkout_configurations"]["purchase_url"] = url
    with pytest.raises(WhopError, match="checkout_response_mismatch"):
        adapter(data, []).create_checkout(TenantContext("tenant-a", "actor-a"), intent(), binding())


def test_catalog_snapshot_must_match() -> None:
    calls: list[httpx.Request] = []
    with pytest.raises(WhopError, match="catalog_binding_mismatch"):
        adapter(resources(), calls).create_checkout(
            TenantContext("tenant-a", "actor-a"), intent(), replace(binding(), amount_minor=9900)
        )
    assert not calls


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("billing_period", 365),
        ("renewal_price", 9),
        ("initial_price", 10),
        ("trial_period_days", 7),
        ("billing_type", "one_time"),
        ("currency", "inr"),
        ("account", {"id": "biz_other"}),
    ],
)
def test_changed_variant_cannot_charge_a_different_contract(key: str, value: object) -> None:
    data = resources()
    data["/api/v1/variants/plan_test"][key] = value
    calls: list[httpx.Request] = []
    with pytest.raises(WhopError, match="variant_contract_mismatch"):
        adapter(data, calls).create_checkout(
            TenantContext("tenant-a", "actor-a"), intent(), binding()
        )
    assert len(calls) == 1


def test_verified_payment_requires_three_independent_reads_and_has_no_grant_side_effect() -> None:
    calls: list[httpx.Request] = []
    purchase = intent()
    charge = adapter(resources(), calls).verify_charge("pay_test", purchase, binding())
    assert charge.tenant_id == "tenant-a" and not charge.revoked
    assert len(calls) == 3 and all(request.method == "GET" for request in calls)
    assert purchase.payment_id is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("status", "pending"),
        ("account_id", "biz_other"),
        ("metadata", {"nsauto_intent_id": "other"}),
        ("variant_id", "plan_other"),
        ("currency", "inr"),
    ],
)
def test_browser_or_other_tenant_payment_cannot_be_verified(key: str, value: object) -> None:
    data = resources()
    data["/api/v1/payments/pay_test"][key] = value
    with pytest.raises(WhopError, match="payment_contract_mismatch"):
        adapter(data, []).verify_charge("pay_test", intent(), binding())


def test_tax_is_separate_but_discounts_and_fractional_quantities_are_rejected() -> None:
    data = resources()
    payment = data["/api/v1/payments/pay_test"]
    payment.update(
        tax_amount={"currency": "usd", "amount": "4.90"},
        total={"currency": "usd", "amount": "53.90"},
    )
    assert not adapter(data, []).verify_charge("pay_test", intent(), binding()).revoked
    payment["total"] = {"currency": "usd", "amount": "52.90"}
    with pytest.raises(WhopError, match="payment_amount_mismatch"):
        adapter(data, []).verify_charge("pay_test", intent(), binding())


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.001", True, 49.0])
def test_money_is_exact_bounded_and_not_binary_float(value: object) -> None:
    with pytest.raises(WhopError):
        minor_amount(value)
    assert minor_amount(Decimal("49.00")) == 4900


@pytest.mark.parametrize("bad", [None, "missing", "currency", "amount", "underpaid"])
def test_localized_item_requires_matching_presentment_and_usd_settlement(bad: str | None) -> None:
    data = resources()
    payment = data["/api/v1/payments/pay_test"]
    payment["line_items"] = [{
        "product_id": "prod_test", "variant_id": "plan_test", "quantity": 1,
        "subtotal": {"currency": "inr", "amount": "4645.00"},
    }]
    payment["presentment_total"] = {"currency": "inr", "amount": "4645.00"}
    payment["presentment_tax_amount"] = {"currency": "inr", "amount": "0.00"}
    if bad == "missing":
        del payment["presentment_total"]
    elif bad == "currency":
        payment["presentment_tax_amount"] = {"currency": "eur", "amount": "0.00"}
    elif bad == "amount":
        payment["presentment_total"] = {"currency": "inr", "amount": "1.00"}
    elif bad == "underpaid":
        payment["total"] = {"currency": "usd", "amount": "1.00"}
    if bad:
        with pytest.raises(WhopError):
            adapter(data, []).verify_charge("pay_test", intent(), binding())
    else:
        assert not adapter(data, []).verify_charge("pay_test", intent(), binding()).revoked


@pytest.mark.parametrize(
    ("resource", "key", "value"),
    [
        ("payments/pay_test", "substatus", "refunded"),
        ("payments/pay_test", "refunded_amount", {"currency": "usd", "amount": "1.00"}),
        ("memberships/mem_test", "status", "canceled"),
        ("memberships/mem_test", "status", "past_due"),
    ],
)
def test_refunds_and_inactive_membership_return_revoked_evidence(
    resource: str, key: str, value: object
) -> None:
    data = resources()
    data["/api/v1/" + resource][key] = value
    assert adapter(data, []).verify_charge("pay_test", intent(), binding()).revoked


def test_signature_and_envelope_validate_before_resource_lookup() -> None:
    raw, headers = signed_notice()
    notice = verify_notice(raw, headers, "ws_synthetic", "biz_test", now=1000)
    assert notice.resource_id == "pay_test"
    headers["webhook-signature"] = "v1,bad"
    with pytest.raises(WhopError, match="invalid_signature"):
        verify_notice(b"not-json", headers, "ws_synthetic", "biz_test", now=1000)


@pytest.mark.parametrize("now", [699, 1301])
def test_old_and_future_signed_events_are_rejected(now: int) -> None:
    raw, headers = signed_notice()
    with pytest.raises(WhopError, match="expired_webhook"):
        verify_notice(raw, headers, "ws_synthetic", "biz_test", now=now)


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "msg_other"},
        {"account_id": "biz_other"},
        {"api_version_date": "2020-01-01"},
        {"type": "product.updated"},
    ],
)
def test_valid_signature_does_not_override_envelope_checks(overrides: dict[str, object]) -> None:
    raw, headers = signed_notice(overrides=overrides)
    with pytest.raises(WhopError):
        verify_notice(raw, headers, "ws_synthetic", "biz_test", now=1000)


def test_provider_failure_is_sanitized_and_not_success() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="sensitive-provider-body")

    client = WhopAdapter(
        WhopSettings("biz_test", "synthetic-key", enabled=True),
        httpx.Client(transport=httpx.MockTransport(fail)),
    )
    with pytest.raises(WhopUnavailable, match="^whop_request_failed$"):
        client.verify_charge("pay_test", intent(), binding())


def test_resource_id_cannot_change_url_path() -> None:
    calls: list[httpx.Request] = []
    with pytest.raises(WhopError):
        adapter(resources(), calls).retrieve("payments", "pay_test/../../memberships")
    assert not calls
