from pathlib import Path

from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_persistence import AgencyWhopPersistence


def test_persistence_rejects_unverified_object_without_database_activity():
    class NoDatabase:
        def query(self, *args, **kwargs):
            raise AssertionError("Must not touch database")
        def rollback(self):
            pass

    service = AgencyWhopPersistence(NoDatabase())
    for untrusted in (None, {}, {"status": "paid"}, "paid"):
        try:
            service.record_verified_purchase(untrusted)
        except ValueError:
            pass
        else:
            raise AssertionError("Untrusted payload accepted")


def test_persistence_requires_provider_scoped_order_and_one_entitlement():
    source = Path(__file__).resolve().parents[1] / "app/services/agency_whop_persistence.py"
    text = source.read_text(encoding="utf-8")
    assert 'payment_provider="whop"' in text
    assert "provider_order_id=purchase.provider_order_id" in text
    assert "AgencyEntitlement(" in text
    assert "AgencyFulfilment(" in text
    assert "self.db.commit()" in text
    assert "self.db.rollback()" in text


def test_verified_contract_produces_whop_order_identity():
    p = validate_verified_whop_purchase(
        independently_verified=True,
        payment_status="paid",
        provider_order_id="synthetic_order",
        provider_product_id="synthetic_product",
        configured_product_map={"synthetic_product": "starter-toolkit"},
        amount="27.00", currency="USD",
        customer_email="buyer@example.com",
    )
    assert p.provider_order_id == "synthetic_order"
    assert p.provider == "whop"


def test_duplicate_whop_order_rejects_conflicting_amount_without_grant():
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import pytest

    purchase = validate_verified_whop_purchase(
        independently_verified=True, payment_status="paid",
        provider_order_id="synthetic_order", provider_product_id="synthetic_product",
        configured_product_map={"synthetic_product": "starter-toolkit"},
        amount="27.00", currency="USD", customer_email="buyer@example.com",
    )
    old_order = SimpleNamespace(
        id="old-id", payment_provider="whop",
        provider_order_id="synthetic_order", provider_product_id="synthetic_product",
        product_key="starter-toolkit", amount=Decimal("26.00"),
        currency="USD", status="completed",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = old_order
    with pytest.raises(ValueError, match="facts conflict"):
        AgencyWhopPersistence(db).record_verified_purchase(purchase)
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
    db.add.assert_not_called()


def test_duplicate_whop_order_rejects_different_customer_email():
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    import pytest

    purchase = validate_verified_whop_purchase(
        independently_verified=True, payment_status="paid",
        provider_order_id="synthetic_order", provider_product_id="synthetic_product",
        configured_product_map={"synthetic_product": "starter-toolkit"},
        amount="27.00", currency="USD", customer_email="new@example.com",
    )
    existing = SimpleNamespace(
        id="order-1", customer_id="customer-1", payment_provider="whop",
        provider_order_id="synthetic_order", provider_product_id="synthetic_product",
        product_key="starter-toolkit", amount=Decimal("27.00"),
        currency="USD", status="completed",
    )
    db = MagicMock()
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = existing
    customer_query = MagicMock()
    customer_query.filter.return_value.first.return_value = SimpleNamespace(email="original@example.com")
    db.query.side_effect = [order_query, customer_query]
    with pytest.raises(ValueError, match="customer conflict"):
        AgencyWhopPersistence(db).record_verified_purchase(purchase)
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
    db.add.assert_not_called()


def test_new_verified_whop_order_creates_single_entitlement_and_fulfilment():
    from unittest.mock import MagicMock
    from app.models.agency_commerce import AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment

    purchase = validate_verified_whop_purchase(
        independently_verified=True, payment_status="paid",
        provider_order_id="new_synthetic_order", provider_product_id="synthetic_product",
        configured_product_map={"synthetic_product": "starter-toolkit"},
        amount="27.00", currency="USD", customer_email="buyer@example.com",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = None
    added = []
    db.add.side_effect = added.append
    result = AgencyWhopPersistence(db).record_verified_purchase(purchase)
    assert result["handled"] is True
    assert result["duplicate"] is False
    assert [type(record) for record in added] == [
        AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment,
    ]
    order = added[1]
    assert order.payment_provider == "whop"
    assert order.provider_order_id == "new_synthetic_order"
    assert order.paddle_transaction_id is None
    assert order.product_key == "starter-toolkit"
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_duplicate_whop_order_without_new_grants():
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    purchase = validate_verified_whop_purchase(
        independently_verified=True, payment_status="paid",
        provider_order_id="existing_synthetic_order",
        provider_product_id="synthetic_product",
        configured_product_map={"synthetic_product": "starter-toolkit"},
        amount="27.00", currency="USD", customer_email="buyer@example.com",
    )
    existing = SimpleNamespace(
        id="order-1", customer_id="customer-1", payment_provider="whop",
        provider_order_id="existing_synthetic_order", provider_product_id="synthetic_product",
        product_key="starter-toolkit", amount=Decimal("27.00"),
        currency="USD", status="completed",
    )
    db = MagicMock()
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = existing
    customer_query = MagicMock()
    customer_query.filter.return_value.first.return_value = SimpleNamespace(email="buyer@example.com")
    db.query.side_effect = [order_query, customer_query]
    result = AgencyWhopPersistence(db).record_verified_purchase(purchase)
    assert result["duplicate"] is True
    db.add.assert_not_called()
    db.commit.assert_not_called()
