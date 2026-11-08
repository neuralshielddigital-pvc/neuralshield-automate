"""Fail-closed normalization of independently verified Agency purchase facts.

This module does not authenticate Whop webhooks or contact Whop. Callers MUST
first verify webhook authenticity and independently retrieve purchase details
from the provider using server-side credentials. No database writes here.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


AGENCY_ONE_TIME_PRICES = {
    "starter-toolkit": Decimal("27.00"),
    "pro-communications": Decimal("67.00"),
    "advanced-operations": Decimal("97.00"),
    "agency-commercial-license": Decimal("197.00"),
}


@dataclass(frozen=True)
class VerifiedAgencyPurchase:
    provider: str
    provider_order_id: str
    provider_product_id: str
    product_key: str
    amount: Decimal
    currency: str
    customer_email: str


def validate_verified_whop_purchase(
    *,
    independently_verified: bool,
    payment_status: str,
    provider_order_id: str,
    provider_product_id: str,
    configured_product_map: dict[str, str],
    amount: str,
    currency: str,
    customer_email: str,
) -> VerifiedAgencyPurchase:
    """Validate *server-confirmed* facts, never browser or raw webhook data.

    Product map is a server-held allowlist of Whop product IDs to Agency keys.
    The integration must not grant any entitlement until this returns AND a
    provider-scoped idempotent database transaction commits.
    """
    if not independently_verified or payment_status != "paid":
        raise ValueError("Payment has not been independently verified as paid")
    if not isinstance(provider_order_id, str) or not provider_order_id.strip():
        raise ValueError("Missing provider order ID")
    if not isinstance(provider_product_id, str) or provider_product_id not in configured_product_map:
        raise ValueError("Unknown provider product")
    key = configured_product_map[provider_product_id]
    if key not in AGENCY_ONE_TIME_PRICES:
        raise ValueError("Unknown Agency product")
    if currency != "USD":
        raise ValueError("Invalid payment currency")
    if not isinstance(amount, str):
        raise ValueError("Amount must be an exact decimal string")
    try:
        value = Decimal(amount)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if not value.is_finite() or value != AGENCY_ONE_TIME_PRICES[key]:
        raise ValueError("Incorrect product amount")
    email = customer_email.strip().lower() if isinstance(customer_email, str) else ""
    if not email or len(email) > 320 or email.count("@") != 1:
        raise ValueError("Missing valid customer email")
    return VerifiedAgencyPurchase(
        provider="whop",
        provider_order_id=provider_order_id.strip(),
        provider_product_id=provider_product_id,
        product_key=key,
        amount=value,
        currency="USD",
        customer_email=email,
    )
