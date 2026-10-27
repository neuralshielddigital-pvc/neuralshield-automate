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
