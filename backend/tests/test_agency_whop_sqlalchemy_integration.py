"""Real SQLAlchemy transaction regression tests; isolated in-memory DB, no production access."""
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.agency_commerce import (
    AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment,
)
from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_persistence import AgencyWhopPersistence


def test_verified_whop_purchase_commits_once_and_duplicate_remains_single():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    tables = [
        AgencyCustomer.__table__, AgencyOrder.__table__,
        AgencyEntitlement.__table__, AgencyFulfilment.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    purchase = validate_verified_whop_purchase(
        independently_verified=True,
        payment_status="paid",
        provider_order_id="sqlite_synthetic_order",
        provider_product_id="sqlite_synthetic_product",
        configured_product_map={"sqlite_synthetic_product": "starter-toolkit"},
        amount="27.00",
        currency="USD",
        customer_email="customer@example.com",
    )
    try:
        with Session(engine) as session:
            first = AgencyWhopPersistence(session).record_verified_purchase(purchase)
            second = AgencyWhopPersistence(session).record_verified_purchase(purchase)
            assert first["duplicate"] is False
            assert second["duplicate"] is True
            assert first["order_id"] == second["order_id"]
            assert session.scalar(select(func.count()).select_from(AgencyCustomer)) == 1
            assert session.scalar(select(func.count()).select_from(AgencyOrder)) == 1
            assert session.scalar(select(func.count()).select_from(AgencyEntitlement)) == 1
            assert session.scalar(select(func.count()).select_from(AgencyFulfilment)) == 1
    finally:
        engine.dispose()
