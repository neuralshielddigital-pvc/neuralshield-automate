from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import db_session, get_current_user
from app.api.routes.auth import login_rate_limit_ready
from app.api.routes.public import public_lead_rate_limit
from app.core.config import settings
from app.main import app
from app.models.enums import UserRole


def make_user(role: UserRole = UserRole.ADMIN) -> SimpleNamespace:
    tenant = SimpleNamespace(
        id=uuid4(),
        name="NeuralShieldDigital",
        slug="neuralshielddigital",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    return SimpleNamespace(
        id=uuid4(),
        email="admin@example.com",
        is_active=True,
        role=role,
        tenant_id=tenant.id,
        tenant=tenant,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def fake_user() -> SimpleNamespace:
    return make_user()


@pytest.fixture
def client(
    fake_user: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    app.dependency_overrides[db_session] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[login_rate_limit_ready] = lambda: None
    app.dependency_overrides[public_lead_rate_limit] = lambda: None

    monkeypatch.setattr(
        "app.main.start_background_worker",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.main.stop_background_worker",
        lambda: None,
    )

    trusted_host = next(
        (
            host
            for host in settings.TRUSTED_HOSTS
            if host and host != "*"
        ),
        "testserver",
    )

    with TestClient(
        app,
        base_url=f"https://{trusted_host}",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def uuid_str() -> str:
    return str(uuid4())


STATIC_UUID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def agency_engine_factory():
    """Use SQLite normally; opt-in PostgreSQL uses disposable schemas only."""
    import os
    from contextlib import contextmanager
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.pool import StaticPool

    @contextmanager
    def factory():
        raw_url = os.environ.get('AGENCY_TEST_DATABASE_URL', '')
        if not raw_url:
            engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
            try:
                yield engine
            finally:
                engine.dispose()
            return
        url = make_url(raw_url)
        if (url.drivername != 'postgresql+psycopg'
                or url.host not in ('127.0.0.1', '::1')
                or not (url.database or '').startswith('nsd_agency_test_')
                or url.query
                or os.environ.get('AGENCY_TEST_ALLOW_ISOLATED_POSTGRES') != 'yes'):
            raise ValueError('Only an explicitly confirmed loopback nsd_agency_test_ database is allowed')
        schema = 'nsd_agency_test_' + uuid4().hex
        control = create_engine(url)
        with control.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(url, connect_args={'options': '-csearch_path=' + schema})
        try:
            yield engine
        finally:
            engine.dispose()
            with control.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
            control.dispose()

    return factory
