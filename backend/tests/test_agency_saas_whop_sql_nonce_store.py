"""Isolated SQLite tests for atomic SQL ownership nonce redemption.

Production must use PostgreSQL and the same database transaction for the
nonce redemption and account binding. No provider requests or paid grants.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine
from sqlalchemy.orm import Session

from app.services.agency_saas_whop_sql_nonce_store import SQLAlchemyAtomicAuthorizationStore


NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)


def test_atomic_redemption_is_single_use_and_identity_bound():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    table = Table(
        "ownership_nonces", metadata,
        Column("nonce", String(128), primary_key=True),
        Column("session_id", String(128), nullable=False),
        Column("user_id", String(128), nullable=False),
        Column("tenant_id", String(128), nullable=False),
        Column("expires_at", DateTime(timezone=True), nullable=False),
        Column("consumed_at", DateTime(timezone=True), nullable=True),
    )
    metadata.create_all(engine)
    with Session(engine) as db:
        db.execute(table.insert().values(
            nonce="nonce-0123456789012345", session_id="session-0123456789012345",
            user_id="user-1", tenant_id="tenant-1",
            expires_at=NOW + timedelta(minutes=5), consumed_at=None,
        ))
        db.commit()
        store = SQLAlchemyAtomicAuthorizationStore(db, table)
        args = dict(nonce="nonce-0123456789012345",
                    session_id="session-0123456789012345",
                    user_id="user-1", tenant_id="tenant-1", now=NOW)
        assert store.consume_if_matches(**{**args, "tenant_id": "other"}) is False
        assert store.consume_if_matches(**{**args, "now": NOW + timedelta(minutes=6)}) is False
        assert store.consume_if_matches(**args) is True
        db.commit()
    with Session(engine) as db:
        assert SQLAlchemyAtomicAuthorizationStore(db, table).consume_if_matches(**args) is False


def test_unaware_clock_rejected():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    table = Table(
        "nonces", metadata,
        Column("nonce", String, primary_key=True),
        Column("session_id", String),
        Column("user_id", String),
        Column("tenant_id", String),
        Column("expires_at", DateTime(timezone=True)),
        Column("consumed_at", DateTime(timezone=True)),
    )
    metadata.create_all(engine)
    with Session(engine) as db:
        store = SQLAlchemyAtomicAuthorizationStore(db, table)
        with pytest.raises(ValueError, match="aware"):
            store.consume_if_matches(
                nonce="n", session_id="s", user_id="u", tenant_id="t",
                now=datetime(2026, 11, 22),
            )
