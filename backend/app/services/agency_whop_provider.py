"""Whop v1 adapter, pinned to the official 2026-11-07 resource contract.

See docs.whop.com/developer/guides/webhooks and /api-reference/payments/retrieve-payment.
Never accept purchase facts from a browser or an unverified webhook.
"""
import base64
import hashlib
import hmac
import json
import re
import time
from decimal import Decimal, InvalidOperation

import requests

from app.services.agency_whop_purchase_lookup import ProviderPurchaseFacts

API_VERSION_DATE = "2026-11-07"


class WhopUnavailable(Exception):
    pass


def verify_signature(payload: bytes, headers, secret: str, *, now=None) -> None:
    event_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signatures = headers.get("webhook-signature", "")
    if not secret.startswith("ws_") or not event_id or len(event_id) > 255:
        raise ValueError("Invalid signature inputs")
    if not timestamp.isdigit() or abs((time.time() if now is None else now) - int(timestamp)) > 300:
        raise ValueError("Expired webhook")
    # Whop uses the literal ws_ secret as HMAC key, not whsec_ decoding.
    signed = event_id.encode() + b"." + timestamp.encode() + b"." + payload
    expected = base64.b64encode(hmac.new(secret.encode(), signed, hashlib.sha256).digest()).decode()
    if not any(hmac.compare_digest(item, "v1," + expected) for item in signatures.split()):
        raise ValueError("Invalid webhook signature")


def money(value) -> Decimal:
    if not isinstance(value, dict) or value.get("currency") != "usd" or not isinstance(value.get("amount"), str):
        raise ValueError("Expected exact USD money")
    try:
        amount = Decimal(value["amount"])
    except InvalidOperation as exc:
        raise ValueError("Invalid money") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid money")
    return amount


class WhopProvider:
    def __init__(self, key: str, account_id: str):
        self.key = key
        self.account_id = account_id

    def retrieve(self, resource: str, identifier: str) -> dict:
        prefixes = {"payments": "pay_", "variants": "plan_", "refunds": "rfnd_"}
        if resource not in prefixes or not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_]{5,255}", identifier):
            raise ValueError("Invalid provider identifier")
        if resource != "refunds" and not identifier.startswith(prefixes[resource]):
            raise ValueError("Invalid provider identifier")
        try:
            response = requests.get(
                f"https://api.whop.com/api/v1/{resource}/{identifier}",
                headers={"Authorization": f"Bearer {self.key}", "Api-Version-Date": API_VERSION_DATE},
                timeout=(2, 3), allow_redirects=False,
            )
            if response.status_code != 200 or len(response.content) > 262144:
                raise WhopUnavailable("Provider lookup failed")
            result = json.loads(response.content, parse_float=Decimal)
        except (requests.RequestException, json.JSONDecodeError) as exc:
            raise WhopUnavailable("Provider lookup failed") from exc
        if not isinstance(result, dict) or result.get("id") != identifier:
            raise ValueError("Provider identity mismatch")
        return result

    def purchase(self, payment_id: str) -> tuple[ProviderPurchaseFacts, bool]:
        payment = self.retrieve("payments", payment_id)
        if payment.get("account_id") != self.account_id or payment.get("status") != "paid":
            raise ValueError("Wrong merchant or unpaid payment")
        if payment.get("currency") != "usd" or payment.get("billing_reason") != "one_time":
            raise ValueError("Not a one-time USD purchase")
        variant = self.retrieve("variants", payment.get("variant_id"))
        if (variant.get("billing_type") != "one_time" or
                (variant.get("account") or {}).get("id") != self.account_id or
                (variant.get("product") or {}).get("id") != payment.get("product_id")):
            raise ValueError("Variant contract mismatch")
        items = payment.get("line_items")
        if not isinstance(items, list) or len(items) != 1:
            raise ValueError("Expected one Agency line item")
        item = items[0]
        if item.get("product_id") != payment.get("product_id") or item.get("variant_id") != variant["id"] or item.get("quantity") != 1:
            raise ValueError("Line item mismatch")
        subtotal = money(payment.get("subtotal"))
        if money(item.get("subtotal")) != subtotal:
            raise ValueError("Subtotal mismatch")
        # Reject discounted/underpaid purchases; tax is separate from catalog price.
        if money(payment.get("total")) - (money(payment["tax_amount"]) if payment.get("tax_amount") is not None else Decimal("0")) != subtotal:
            raise ValueError("Payment amount mismatch")
        revoked = (money(payment["refunded_amount"]) if payment.get("refunded_amount") is not None else Decimal("0")) > 0 or payment.get("substatus") != "succeeded"
        return ProviderPurchaseFacts(
            order_id=payment_id, product_id=payment.get("product_id"), status="paid",
            amount_usd=str(subtotal), currency="USD", customer_email=payment.get("customer_email"),
        ), revoked
