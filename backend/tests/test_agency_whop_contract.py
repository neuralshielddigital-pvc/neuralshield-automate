import pytest

from app.services.agency_whop_contract import validate_verified_whop_purchase

BASE = dict(
    independently_verified=True,
    payment_status="paid",
    provider_order_id="purchase_test_1",
    provider_product_id="product_test_1",
    configured_product_map={"product_test_1": "starter-toolkit"},
    amount="27.00",
    currency="USD",
    customer_email="Buyer@Example.com",
)


def test_verified_purchase_contract_accepts_only_exact_match():
    result = validate_verified_whop_purchase(**BASE)
    assert result.provider == "whop"
    assert result.product_key == "starter-toolkit"
    assert result.customer_email == "buyer@example.com"


@pytest.mark.parametrize(
    "change",
    [
        {"independently_verified": False},
        {"payment_status": "pending"},
        {"payment_status": "refunded"},
        {"provider_order_id": ""},
        {"provider_product_id": "unknown"},
        {"configured_product_map": {"product_test_1": "invalid"}},
        {"amount": "0"},
        {"amount": "27.01"},
        {"amount": "NaN"},
        {"amount": "Infinity"},
        {"amount": 27.00},
        {"currency": "EUR"},
        {"customer_email": ""},
    ],
)
def test_unverified_or_mismatched_purchase_is_rejected(change):
    with pytest.raises(ValueError):
        validate_verified_whop_purchase(**{**BASE, **change})
