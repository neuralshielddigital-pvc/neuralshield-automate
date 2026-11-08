from dataclasses import replace

from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_fulfillment_policy import decide_whop_fulfillment

purchase = validate_verified_whop_purchase(
    independently_verified=True,
    payment_status="paid",
    provider_order_id="synthetic-order",
    provider_product_id="synthetic-product",
    configured_product_map={"synthetic-product": "starter-toolkit"},
    amount="27.00",
    currency="USD",
    customer_email="buyer@example.com",
)


def test_new_verified_purchase_may_proceed_to_transactional_persistence():
    result = decide_whop_fulfillment(
        purchase,
        existing_order_provider=None,
        existing_order_id=None,
        existing_order_product_key=None,
    )
    assert result.action == "grant"


def test_duplicate_verified_order_is_idempotent():
    result = decide_whop_fulfillment(
        purchase,
        existing_order_provider="whop",
        existing_order_id="synthetic-order",
        existing_order_product_key="starter-toolkit",
    )
    assert result.action == "duplicate"


def test_conflict_refund_and_cross_provider_never_grant():
    for values in (
        {"existing_order_provider": "paddle", "existing_order_id": "synthetic-order", "existing_order_product_key": "starter-toolkit"},
        {"existing_order_provider": "whop", "existing_order_id": "synthetic-order", "existing_order_product_key": "advanced-operations"},
        {"existing_order_provider": None, "existing_order_id": None, "existing_order_product_key": None, "payment_reversed": True},
    ):
        assert decide_whop_fulfillment(purchase, **values).action == "reject"
    assert decide_whop_fulfillment(
        replace(purchase, provider="paddle"),
        existing_order_provider=None,
        existing_order_id=None,
        existing_order_product_key=None,
    ).action == "reject"
