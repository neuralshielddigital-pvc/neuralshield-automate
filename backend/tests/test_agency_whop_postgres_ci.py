"""Disposable PostgreSQL integration test; never connects to production DB."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.agency_commerce import (
    AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment,
)
from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_persistence import AgencyWhopPersistence


def test_whop_postgresql_verified_purchase_and_replay():
    url = os.environ.get("AGENCY_WHOP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Only run with isolated CI PostgreSQL database")
    if not url.startswith("postgresql") or "127.0.0.1" not in url:
        pytest.fail("Whop PostgreSQL test requires isolated loopback database")
    engine = create_engine(url)
    tables = [AgencyCustomer.__table__, AgencyOrder.__table__,
              AgencyEntitlement.__table__, AgencyFulfilment.__table__]
    unique = uuid4().hex
    try:
        Base.metadata.create_all(engine, tables=tables)
        purchase = validate_verified_whop_purchase(
            independently_verified=True, payment_status="paid",
            provider_order_id=f"ci_{unique}",
            provider_product_id="ci_product",
            configured_product_map={"ci_product": "starter-toolkit"},
            amount="27.00", currency="USD",
            customer_email=f"ci_{unique}@example.com",
        )
        with Session(engine) as db:
            first = AgencyWhopPersistence(db).record_verified_purchase(purchase)
            second = AgencyWhopPersistence(db).record_verified_purchase(purchase)
            assert first["duplicate"] is False
            assert second["duplicate"] is True
            assert first["order_id"] == second["order_id"]
            assert db.scalar(select(func.count()).select_from(AgencyOrder)) == 1
            assert db.scalar(select(func.count()).select_from(AgencyEntitlement)) == 1
            assert db.scalar(select(func.count()).select_from(AgencyFulfilment)) == 1
    finally:
        Base.metadata.drop_all(engine, tables=list(reversed(tables)))
        engine.dispose()
