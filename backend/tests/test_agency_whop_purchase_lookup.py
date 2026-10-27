import pytest

from app.services.agency_whop_purchase_lookup import (
    ProviderPurchaseFacts,
    prepare_verified_whop_purchase,
)


class FakeProvider:
    def __init__(self, facts):
        self.facts = facts
        self.calls = []

    def fetch_authenticated_purchase(self, order_id):
        self.calls.append(order_id)
        return self.facts


BASE = ProviderPurchaseFacts(
    order_id="order_synthetic_1",
    product_id="product_synthetic_1",
    status="paid",
    amount_usd="27.00",
    currency="USD",
    customer_email="buyer@example.com",
)
MAP = {"product_synthetic_1": "starter-toolkit"}


def test_authenticated_purchase_lookup_is_required_for_grant_eligibility():
    provider = FakeProvider(BASE)
    result = prepare_verified_whop_purchase(
        order_id="order_synthetic_1", lookup=provider, product_map=MAP,
    )
    assert result.product_key == "starter-toolkit"
    assert provider.calls == ["order_synthetic_1"]


@pytest.mark.parametrize("facts", [
    ProviderPurchaseFacts(**{**BASE.__dict__, "order_id": "different"}),
    ProviderPurchaseFacts(**{**BASE.__dict__, "status": "pending"}),
    ProviderPurchaseFacts(**{**BASE.__dict__, "status": "refunded"}),
    ProviderPurchaseFacts(**{**BASE.__dict__, "amount_usd": "26.99"}),
    ProviderPurchaseFacts(**{**BASE.__dict__, "currency": "EUR"}),
])
def test_invalid_provider_verified_facts_rejected(facts):
    with pytest.raises(ValueError):
        prepare_verified_whop_purchase(
            order_id="order_synthetic_1",
            lookup=FakeProvider(facts),
            product_map=MAP,
        )


def test_missing_or_invalid_provider_response_rejected():
    for response in (None, {}, "paid"):
        with pytest.raises(ValueError):
            prepare_verified_whop_purchase(
                order_id="order_synthetic_1",
                lookup=FakeProvider(response),
                product_map=MAP,
            )
    with pytest.raises(ValueError):
        prepare_verified_whop_purchase(
            order_id="", lookup=FakeProvider(BASE), product_map=MAP,
        )
