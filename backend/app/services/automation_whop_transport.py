"""Strict Whop v1 transport for Automation SaaS; adapted from verified checkout code.

Checkout intents must be persisted and authorized before calling this adapter.
VerifiedCharge is evidence for a reconciler, never a license grant by itself.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import urlsplit, urlencode

import httpx

from app.services.automation_whop_contract import (
    CheckoutIntent,
    ProvisioningState,
    TenantContext,
    require_owner,
)

API_VERSION_DATE = "2026-11-07"
MAX_BODY = 262_144
RETURN_URL = "https://app.neuralshielddigital.com/dashboard/billing"
ORIGINS = {
    "sandbox": "https://sandbox-api.whop.com/api/v1",
    "production": "https://api.whop.com/api/v1",
}


class WhopError(ValueError):
    """Sanitized contract error; never includes provider payloads or credentials."""


class WhopUnavailable(RuntimeError):
    """The caller must retry reconciliation, never acknowledge/grant on failure."""


def identifier(value: object, prefix: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(prefix + r"[A-Za-z0-9]{1,200}", value):
        raise WhopError("invalid_provider_identifier")
    return value


def minor_amount(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise WhopError("invalid_money")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise WhopError("invalid_money") from exc
    if not amount.is_finite() or amount < 0 or amount > Decimal("1000000"):
        raise WhopError("invalid_money")
    minor = amount * 100
    if minor != minor.to_integral_value():
        raise WhopError("invalid_money_precision")
    return int(minor)


def money(value: object) -> int:
    obj = object_value(value)
    if obj.get("currency") != "usd":
        raise WhopError("wrong_currency")
    return minor_amount(obj.get("amount"))


def object_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise WhopError("invalid_object")
    return value


def line_subtotal(payment: dict[str, object], item: dict[str, object]) -> int:
    """Bind a localized single item to authenticated presentment and USD settlement."""
    value = object_value(item.get("subtotal"))
    currency = value.get("currency")
    if currency == "usd":
        return money(value)
    if not isinstance(currency, str) or not re.fullmatch(r"[a-z]{3}", currency):
        raise WhopError("invalid_presentment_currency")

    def local_amount(raw: object) -> int:
        obj = object_value(raw)
        if obj.get("currency") != currency or not isinstance(obj.get("amount"), str):
            raise WhopError("presentment_currency_mismatch")
        return minor_amount(obj.get("amount"))

    amount = local_amount(value)
    total = local_amount(payment.get("presentment_total"))
    tax = local_amount(payment.get("presentment_tax_amount"))
    if amount <= 0 or total - tax != amount:
        raise WhopError("presentment_amount_mismatch")
    return money(payment.get("subtotal"))


@dataclass(frozen=True)
class WhopBinding:
    catalog_version: str
    plan_code: str
    product_id: str
    variant_id: str
    amount_minor: int
    interval: Literal["month", "year"]

    def __post_init__(self) -> None:
        identifier(self.product_id, "prod_")
        identifier(self.variant_id, "plan_")
        if (
            not 1 <= len(self.catalog_version) <= 100
            or not 1 <= len(self.plan_code) <= 60
            or type(self.amount_minor) is not int
            or not 1 <= self.amount_minor <= 100_000_000
            or self.interval not in {"month", "year"}
        ):
            raise WhopError("invalid_catalog_binding")


@dataclass(frozen=True)
class WhopSettings:
    account_id: str
    api_key: str = field(repr=False)
    environment: Literal["sandbox", "production"] = "sandbox"
    enabled: bool = False

    def require_enabled(self) -> None:
        if self.enabled is not True:
            raise WhopError("whop_disabled")
        identifier(self.account_id, "biz_")
        if (
            self.environment not in ORIGINS
            or not self.api_key
            or any(char in self.api_key for char in "\r\n")
        ):
            raise WhopError("invalid_whop_configuration")


@dataclass(frozen=True)
class WebhookNotice:
    event_id: str
    event_type: str
    resource_id: str


def verify_notice(
    raw: bytes,
    headers: dict[str, str],
    secret: str,
    account_id: str,
    *,
    now: int,
) -> WebhookNotice:
    """Verify literal ws_ HMAC, bounded timestamp, envelope and merchant before lookup."""
    identifier(account_id, "biz_")
    event_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signatures = headers.get("webhook-signature", "")
    if (
        not secret.startswith("ws_")
        or len(secret) < 8
        or len(secret) > 512
        or not 1 <= len(event_id) <= 255
        or not event_id.isascii()
        or not re.fullmatch(r"[A-Za-z0-9_-]+", event_id)
        or not re.fullmatch(r"[0-9]{1,12}", timestamp)
        or len(raw) > MAX_BODY
        or len(signatures) > 4096
        or not signatures.isascii()
    ):
        raise WhopError("invalid_webhook")
    if abs(now - int(timestamp)) > 300:
        raise WhopError("expired_webhook")
    signed = event_id.encode() + b"." + timestamp.encode() + b"." + raw
    expected = (
        "v1,"
        + base64.b64encode(hmac.new(secret.encode(), signed, hashlib.sha256).digest()).decode()
    )
    if not any(hmac.compare_digest(item, expected) for item in signatures.split()):
        raise WhopError("invalid_signature")
    try:
        envelope = object_value(json.loads(raw))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WhopError("invalid_webhook_json") from exc
    if (
        envelope.get("id") != event_id
        or envelope.get("account_id") != account_id
        or envelope.get("api_version") != "v1"
        or envelope.get("api_version_date") != API_VERSION_DATE
    ):
        raise WhopError("webhook_envelope_mismatch")
    event_type = envelope.get("type")
    prefixes = {
        "payment.succeeded": "pay_",
        "payment.failed": "pay_",
        "membership.activated": "mem_",
        "membership.deactivated": "mem_",
        "membership.updated": "mem_",
    }
    if not isinstance(event_type, str) or event_type not in prefixes:
        raise WhopError("unsupported_event")
    resource_id = identifier(object_value(envelope.get("data")).get("id"), prefixes[event_type])
    return WebhookNotice(event_id, event_type, resource_id)


@dataclass(frozen=True)
class HostedCheckout:
    configuration_id: str
    purchase_url: str


@dataclass(frozen=True)
class VerifiedCharge:
    payment_id: str
    membership_id: str
    intent_id: str
    tenant_id: str
    catalog_version: str
    plan_code: str
    revoked: bool


@dataclass(frozen=True)
class VerifiedPaidPeriod:
    charge: VerifiedCharge
    checked_at: datetime
    starts_at: datetime | None
    ends_at: datetime | None
    customer_id: str | None = None
    cancel_at_period_end: bool = False


def provider_timestamp(value: object) -> datetime:
    if (
        not isinstance(value, str)
        or not 20 <= len(value) <= 40
        or value.strip() != value
        or "T" not in value
    ):
        raise WhopError("invalid_membership_period")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone_required")
        return parsed.astimezone(UTC)
    except ValueError as exc:
        raise WhopError("invalid_membership_period") from exc


class WhopAdapter:
    def __init__(self, settings: WhopSettings, client: httpx.Client) -> None:
        self.settings = settings
        self.client = client

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        self.settings.require_enabled()
        # Fixed origins only. No customer/provider-controlled URL is requested.
        try:
            with self.client.stream(
                method,
                ORIGINS[self.settings.environment] + path,
                headers={
                    "Authorization": "Bearer " + self.settings.api_key,
                    "Api-Version-Date": API_VERSION_DATE,
                    **({"Idempotency-Key": idempotency_key} if idempotency_key else {}),
                },
                json=payload,
                timeout=10,
                follow_redirects=False,
            ) as response:
                if response.status_code not in {200, 201}:
                    raise WhopUnavailable("whop_request_failed")
                body = bytearray()
                for part in response.iter_bytes():
                    body.extend(part)
                    if len(body) > MAX_BODY:
                        raise WhopUnavailable("whop_response_too_large")
                return object_value(json.loads(body, parse_float=Decimal))
        except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WhopUnavailable("whop_request_failed") from exc

    def retrieve(self, resource: str, resource_id: str) -> dict[str, object]:
        prefixes = {"payments": "pay_", "variants": "plan_", "memberships": "mem_"}
        if resource not in prefixes:
            raise WhopError("unsupported_resource")
        identifier(resource_id, prefixes[resource])
        result = self._request("GET", "/" + resource + "/" + resource_id)
        if result.get("id") != resource_id:
            raise WhopError("provider_identity_mismatch")
        return result

    def payment_candidates(self, membership_id: str, starts: datetime) -> list[str]:
        """Bounded discovery only; every candidate must be retrieved and verified.

        A truncated list fails closed instead of guessing which receipt is paid.
        """
        identifier(membership_id, "mem_")
        query = urlencode({"account_id": self.settings.account_id,
                           "membership_id": membership_id, "first": 10,
                           "created_after": (starts - timedelta(days=7)).isoformat(),
                           "order": "created_at", "direction": "desc"})
        result = self._request("GET", "/payments?" + query)
        items = result.get("data")
        info = object_value(result.get("page_info"))
        if not isinstance(items, list) or len(items) > 10 or info.get("has_next_page") is not False:
            raise WhopError("payment_discovery_incomplete")
        return [identifier(object_value(item).get("id"), "pay_") for item in items]

    def _binding(self, intent: CheckoutIntent, binding: WhopBinding) -> None:
        if (
            intent.plan.catalog_version != binding.catalog_version
            or intent.plan.code != binding.plan_code
            or intent.plan.currency != "USD"
            or intent.plan.amount_minor != binding.amount_minor
            or intent.plan.interval != binding.interval
        ):
            raise WhopError("catalog_binding_mismatch")

    def _metadata(self, intent: CheckoutIntent) -> dict[str, object]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", intent.id):
            raise WhopError("invalid_intent_id")
        return {
            "nsauto_intent_id": intent.id,
            "nsauto_catalog_version": intent.plan.catalog_version,
            "nsauto_tenant_id": intent.tenant_id,
        }

    def _variant(self, binding: WhopBinding) -> None:
        variant = self.retrieve("variants", binding.variant_id)
        if (
            object_value(variant.get("account")).get("id") != self.settings.account_id
            or object_value(variant.get("product")).get("id") != binding.product_id
            or variant.get("billing_type") != "renewal"
            or variant.get("currency") != "usd"
            or variant.get("billing_period") != {"month": 30, "year": 365}[binding.interval]
            or minor_amount(variant.get("renewal_price")) != binding.amount_minor
            or minor_amount(variant.get("initial_price")) != 0
            or variant.get("trial_period_days") not in {None, 0}
        ):
            raise WhopError("variant_contract_mismatch")

    def create_checkout(
        self,
        ctx: TenantContext,
        intent: CheckoutIntent,
        binding: WhopBinding,
    ) -> HostedCheckout:
        # ctx must originate from the authenticated application user and DB tenant.
        require_owner(ctx, intent.tenant_id)
        self._binding(intent, binding)
        if intent.state != ProvisioningState.PENDING_PAYMENT:
            raise WhopError("checkout_not_pending")
        metadata = self._metadata(intent)
        self._variant(binding)
        result = self._request(
            "POST",
            "/checkout_configurations",
            {
                "account_id": self.settings.account_id,
                "variant_id": binding.variant_id,
                "mode": "payment",
                "metadata": metadata,
                "redirect_url": RETURN_URL,
            },
            idempotency_key="nsauto-checkout-" + intent.id,
        )
        config_id = identifier(result.get("id"), "ch_")
        url = result.get("purchase_url")
        if not isinstance(url, str):
            raise WhopError("invalid_checkout_url")
        parsed = urlsplit(url)
        host = "whop.com" if self.settings.environment == "production" else "sandbox.whop.com"
        if (
            parsed.scheme != "https"
            or parsed.netloc != host
            or parsed.path.rstrip("/") != "/checkout/" + config_id
            or parsed.query
            or parsed.fragment
            or result.get("account_id") != self.settings.account_id
            or result.get("mode") != "payment"
            or result.get("metadata") != metadata
            or object_value(result.get("variant")).get("id") != binding.variant_id
        ):
            raise WhopError("checkout_response_mismatch")
        return HostedCheckout(config_id, url)

    def verify_charge(
        self,
        payment_id: str,
        intent: CheckoutIntent,
        binding: WhopBinding,
    ) -> VerifiedCharge:
        """Independent read only; intent must be loaded from trusted durable storage."""
        return self._verified_resources(payment_id, intent, binding)[0]

    def _verified_resources(
        self,
        payment_id: str,
        intent: CheckoutIntent,
        binding: WhopBinding,
    ) -> tuple[VerifiedCharge, dict[str, object], dict[str, object]]:
        self._binding(intent, binding)
        payment = self.retrieve("payments", payment_id)
        if (
            payment.get("account_id") != self.settings.account_id
            or payment.get("status") != "paid"
            or payment.get("currency") != "usd"
            or payment.get("variant_id") != binding.variant_id
            or payment.get("product_id") != binding.product_id
            or payment.get("metadata") != self._metadata(intent)
        ):
            raise WhopError("payment_contract_mismatch")
        self._variant(binding)
        items = payment.get("line_items")
        if not isinstance(items, list) or len(items) != 1:
            raise WhopError("invalid_line_items")
        item = object_value(items[0])
        subtotal = money(payment.get("subtotal"))
        tax = 0 if payment.get("tax_amount") is None else money(payment.get("tax_amount"))
        if (
            item.get("product_id") != binding.product_id
            or item.get("variant_id") != binding.variant_id
            or type(item.get("quantity")) is not int
            or item.get("quantity") != 1
            or line_subtotal(payment, item) != subtotal
            or subtotal != binding.amount_minor
            or money(payment.get("total")) - tax != subtotal
        ):
            raise WhopError("payment_amount_mismatch")
        membership_id = identifier(payment.get("membership_id"), "mem_")
        membership = self.retrieve("memberships", membership_id)
        if (
            object_value(membership.get("account")).get("id") != self.settings.account_id
            or membership.get("variant_id") != binding.variant_id
            or membership.get("product_id") != binding.product_id
            or membership.get("metadata") != self._metadata(intent)
        ):
            raise WhopError("membership_contract_mismatch")
        refunded = (
            money(payment["refunded_amount"]) if payment.get("refunded_amount") is not None else 0
        )
        revoked = (
            refunded > 0
            or payment.get("substatus") != "succeeded"
            or membership.get("status") != "active"
        )
        charge = VerifiedCharge(
            payment_id,
            membership_id,
            intent.id,
            intent.tenant_id,
            intent.plan.catalog_version,
            intent.plan.code,
            revoked,
        )
        return charge, payment, membership

    def verify_paid_period(
        self,
        payment_id: str,
        intent: CheckoutIntent,
        binding: WhopBinding,
        *,
        now: datetime,
    ) -> VerifiedPaidPeriod:
        """Bind a paid receipt to this membership period, not a later renewal.

        A revoked receipt is negative evidence only, even with missing period
        data. Positive evidence requires a current bounded monthly period and a
        payment actually collected inside that period. No access is granted here.
        """
        if now.tzinfo is None or now.utcoffset() is None:
            raise WhopError("verification_clock_required")
        checked = now.astimezone(UTC)
        charge, payment, membership = self._verified_resources(payment_id, intent, binding)
        if charge.revoked:
            return VerifiedPaidPeriod(charge, checked, None, None)
        starts = provider_timestamp(membership.get("current_period_start"))
        ends = provider_timestamp(membership.get("current_period_end"))
        paid = provider_timestamp(payment.get("paid_at"))
        if (
            binding.interval != "month"
            or membership.get("billing_period_days") != 30
            or type(membership.get("billing_period_days")) is not int
            or not timedelta(0) < ends - starts <= timedelta(days=31)
            or starts > checked
            or ends <= checked
            or not starts <= paid < ends
            or paid > checked + timedelta(seconds=30)
        ):
            raise WhopError("payment_period_mismatch")
        customer_id = identifier(membership.get("user_id"), "user_")
        if type(membership.get("cancel_at_period_end")) is not bool:
            raise WhopError("invalid_cancellation_flag")
        return VerifiedPaidPeriod(charge, checked, starts, ends, customer_id, membership["cancel_at_period_end"])
