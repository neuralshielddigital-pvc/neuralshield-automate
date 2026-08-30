from app.models import Base
from app.models.agency_commerce import (
    AgencyCustomer,
    AgencyEntitlement,
    AgencyFulfilment,
    AgencyOrder,
)


def test_agency_commerce_tables_registered() -> None:
    expected = {
        "agency_customers",
        "agency_orders",
        "agency_entitlements",
        "agency_fulfilments",
    }

    assert expected.issubset(set(Base.metadata.tables))


def test_agency_customer_identity_constraints() -> None:
    table = AgencyCustomer.__table__

    assert table.c.email.unique is True
    assert table.c.paddle_customer_id.unique is True


def test_agency_order_transaction_is_idempotency_key() -> None:
    table = AgencyOrder.__table__

    assert table.c.paddle_transaction_id.unique is True
    assert table.c.paddle_price_id.nullable is False
    assert table.c.product_key.nullable is False


def test_agency_entitlement_links_customer_and_order() -> None:
    table = AgencyEntitlement.__table__

    assert table.c.customer_id.nullable is False
    assert table.c.order_id.nullable is False
    assert table.c.product_key.nullable is False


def test_agency_fulfilment_is_one_per_entitlement() -> None:
    table = AgencyFulfilment.__table__

    assert table.c.entitlement_id.unique is True
    assert table.c.status.nullable is False
