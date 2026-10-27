from unittest.mock import Mock

import pytest

from app.services.agency_whop_purchase_lookup import ProviderPurchaseFacts
from app.services.agency_whop_reconciliation import reconcile_authenticated_whop_purchase


class Provider:
    def __init__(self, status="paid"):
        self.status = status
        self.calls = 0

    def fetch_authenticated_purchase(self, order_id):
        self.calls += 1
        return ProviderPurchaseFacts(
            order_id=order_id,
            product_id="synthetic_product",
            status=self.status,
            amount_usd="27.00",
            currency="USD",
            customer_email="buyer@example.com",
        )


def test_reconciliation_requires_authentication_before_provider_lookup():
    provider, persistence = Provider(), Mock()
    with pytest.raises(ValueError, match="Authenticated"):
        reconcile_authenticated_whop_purchase(
            order_id="synthetic_order", lookup=provider,
            product_map={"synthetic_product": "starter-toolkit"},
            persistence=persistence, webhook_authenticated=False,
        )
    assert provider.calls == 0
    persistence.record_verified_purchase.assert_not_called()


def test_reconciliation_rejects_unpaid_before_persistence():
    provider, persistence = Provider(status="pending"), Mock()
    with pytest.raises(ValueError):
        reconcile_authenticated_whop_purchase(
            order_id="synthetic_order", lookup=provider,
            product_map={"synthetic_product": "starter-toolkit"},
            persistence=persistence, webhook_authenticated=True,
        )
    persistence.record_verified_purchase.assert_not_called()


def test_reconciliation_passes_only_verified_purchase_to_persistence():
    provider, persistence = Provider(), Mock()
    persistence.record_verified_purchase.return_value = {"handled": True}
    result = reconcile_authenticated_whop_purchase(
        order_id="synthetic_order", lookup=provider,
        product_map={"synthetic_product": "starter-toolkit"},
        persistence=persistence, webhook_authenticated=True,
    )
    assert result == {"handled": True}
    purchase = persistence.record_verified_purchase.call_args.args[0]
    assert purchase.provider == "whop"
    assert purchase.amount == 27
    assert provider.calls == 1
