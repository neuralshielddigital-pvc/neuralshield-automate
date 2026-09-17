"""No external provider or SMTP calls. Real local SQL, signature and HTTP routes."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import db_session
from app.api.routes.agency_member import router as member_router
from app.api.routes.paddle_webhook import router as webhook_router
from app.core.config import settings
from app.models.agency_commerce import AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment, AgencyMemberAccessToken
from app.models.system import WebhookEvent
from app.services.agency_commerce_service import AgencyCommerceService
from app.services.agency_delivery_service import AgencyDeliveryService
from app.services.agency_member_service import AgencyMemberService


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(element, compiler, **kw):
    return 'JSON'


class Provider:
    def __init__(self, transaction):
        self.transaction = transaction
        self.customer = {'id': transaction['customer_id'], 'status': 'active', 'email': 'buyer@example.com'}
        self.calls = []
        self.fail = False

    def _api_request(self, method, path):
        assert method == 'GET'
        self.calls.append(path)
        if self.fail:
            raise RuntimeError('do not persist this provider payload')
        return {'data': self.transaction if path.startswith('/transactions/') else self.customer}


class Mailer:
    def __init__(self):
        self.messages = []
        self.config_missing = False
        self.fail = False

    def _validate_config(self):
        if self.config_missing:
            raise ValueError('config incomplete')

    def send_email(self, **message):
        self.messages.append(message)
        if self.fail:
            raise TimeoutError('SMTP acceptance unknown: private details')
        return {'status': 'sent'}


@pytest.fixture
def flow(monkeypatch):
    monkeypatch.setattr(settings, 'AGENCY_STARTER_DELIVERY_ENABLED', True)
    monkeypatch.setattr(settings, 'PADDLE_ENVIRONMENT', 'sandbox')
    monkeypatch.setattr(settings, 'PADDLE_API_BASE_URL', 'https://sandbox-api.paddle.com')
    monkeypatch.setattr(settings, 'PADDLE_API_KEY', 'synthetic-test-key-never-sent')
    monkeypatch.setattr(settings, 'PADDLE_WEBHOOK_SECRET', 'synthetic-test-webhook-secret')
    monkeypatch.setattr(settings, 'SECRET_KEY', 'synthetic-session-secret-for-tests-only')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    for model in (AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment, AgencyMemberAccessToken, WebhookEvent):
        model.__table__.create(engine)
    transaction = {
        'id': 'txn_' + uuid4().hex[:26], 'customer_id': 'ctm_' + uuid4().hex[:26],
        'status': 'completed', 'currency_code': 'USD',
        'items': [{'quantity': 1, 'price': {'id': 'pri_01kzx9mrs5g2bxgjgqwfcb4med', 'unit_price': {'amount': '2700', 'currency_code': 'USD'}, 'billing_cycle': None}}],
        'details': {'totals': {'total': '2700'}},
        'custom_data': {'email': 'untrusted@example.com'},
    }
    with Session(engine) as db:
        app = FastAPI()
        app.include_router(member_router, prefix='/api')
        app.include_router(webhook_router, prefix='/api')
        app.dependency_overrides[db_session] = lambda: db
        with TestClient(app) as client:
            yield db, client, transaction, Provider(transaction), Mailer()
    engine.dispose()


def webhook(client, transaction, event_id='evt_synthetic_completed', signature_valid=True):
    payload = json.dumps({'event_id': event_id, 'event_type': 'transaction.completed', 'data': transaction}).encode()
    timestamp = int(time.time())
    digest = hmac.new(settings.PADDLE_WEBHOOK_SECRET.encode(), str(timestamp).encode() + b':' + payload, hashlib.sha256).hexdigest()
    signature = f'ts={timestamp};h1={digest if signature_valid else "invalid"}'
    return client.post('/api/paddle/webhook', content=payload, headers={'Paddle-Signature': signature})


def queue(flow):
    db, client, transaction, provider, mailer = flow
    assert webhook(client, transaction).status_code == 200
    return db.query(AgencyFulfilment).one(), AgencyDeliveryService(db, provider, mailer)


def test_signed_payment_to_email_link_to_protected_download(flow):
    db, client, txn, provider, mailer = flow
    row, service = queue(flow)
    assert db.query(AgencyCustomer).one().email is None
    assert service.run_batch()['processed'] == 1
    assert len(mailer.messages) == 1
    assert mailer.messages[0]['to_email'] == 'buyer@example.com'
    raw_token = re.search(r'\?token=([^\s]+)', mailer.messages[0]['body']).group(1)
    record = db.query(AgencyMemberAccessToken).one()
    assert record.token_hash != raw_token
    assert row.status == 'email_submitted'
    assert row.email_submitted_at is not None and row.delivered_at is None
    response = client.post('/api/agency-member/consume', json={'token': raw_token})
    assert response.status_code == 200
    session = response.json()['member_token']
    download = client.get('/api/agency-member/resources/starter-download-pack', headers={'Authorization': 'Bearer ' + session})
    assert download.status_code == 200 and download.content.startswith(b'PK')
    assert client.post('/api/agency-member/consume', json={'token': raw_token}).status_code == 401
    assert webhook(client, txn).json()['duplicate'] is True
    assert webhook(client, txn, 'evt_second_notification').status_code == 200
    assert service.run_batch()['processed'] == 0
    assert len(mailer.messages) == 1
    assert db.query(AgencyOrder).count() == 1 and db.query(AgencyEntitlement).count() == 1


def test_invalid_signature_never_queues_delivery(flow):
    db, client, txn, _, mailer = flow
    assert webhook(client, txn, signature_valid=False).status_code == 400
    assert db.query(AgencyFulfilment).count() == 0 and not mailer.messages


def test_disabled_delivery_performs_no_calls(flow, monkeypatch):
    _, _, _, provider, mailer = flow
    row, service = queue(flow)
    monkeypatch.setattr(settings, 'AGENCY_STARTER_DELIVERY_ENABLED', False)
    assert service.run_batch() == {'enabled': False, 'processed': 0}
    assert not service.process_one(row.id)
    assert not provider.calls and not mailer.messages


def test_lookup_retries_are_due_time_gated_and_bounded(flow):
    db, _, _, provider, mailer = flow
    row, service = queue(flow)
    provider.fail = True
    for attempt in (1, 2, 3):
        assert service.run_batch()['processed'] == 1
        assert row.attempt_count == attempt
        assert service.run_batch()['processed'] == 0
        if attempt < 3:
            assert row.status == 'retry_wait'
            row.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
    assert row.status == 'failed'
    assert row.last_error == 'paddle_lookup_failed'
    assert not mailer.messages


def test_retry_recovers_when_provider_recovers(flow):
    db, _, _, provider, mailer = flow
    row, service = queue(flow)
    provider.fail = True
    service.run_batch()
    provider.fail = False
    row.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    service.run_batch()
    assert row.status == 'email_submitted' and len(mailer.messages) == 1


def test_smtp_uncertainty_is_not_automatically_retried(flow):
    _, _, _, _, mailer = flow
    row, service = queue(flow)
    mailer.fail = True
    service.run_batch()
    assert row.status == 'delivery_unknown' and row.last_error == 'smtp_outcome_unknown'
    service.run_batch()
    assert len(mailer.messages) == 1 and row.delivered_at is None


@pytest.mark.parametrize('case', ['customer_id', 'transaction_id', 'email', 'price', 'status', 'legacy_email'])
def test_mismatches_never_send(flow, case):
    db, _, _, provider, mailer = flow
    row, service = queue(flow)
    if case == 'customer_id': provider.customer['id'] = 'ctm_' + 'x' * 26
    if case == 'transaction_id': provider.transaction['id'] = 'txn_' + 'x' * 26
    if case == 'email': provider.customer['email'] = 'invalid\naddress'
    if case == 'price': provider.transaction['items'] = []
    if case == 'status': provider.transaction['status'] = 'paid'
    if case == 'legacy_email':
        db.query(AgencyCustomer).one().email = 'old-unverified@example.com'
        db.commit()
    service.run_batch()
    assert row.status == 'failed' and not mailer.messages


def test_revoked_purchase_never_sends(flow):
    db, _, _, _, mailer = flow
    row, service = queue(flow)
    db.query(AgencyEntitlement).one().status = 'revoked'
    db.commit()
    service.run_batch()
    assert row.status == 'failed' and not mailer.messages


def test_competing_worker_cannot_claim_processing_row(flow):
    db, _, _, _, mailer = flow
    row, service = queue(flow)
    row.status = 'processing'
    row.claimed_at = datetime.now(timezone.utc)
    row.attempt_count = 1
    db.commit()
    assert service.process_one(row.id) is False and not mailer.messages


@pytest.mark.parametrize(('status', 'expected'), [('processing', 'email_submitted'), ('sending', 'delivery_unknown')])
def test_stale_claim_recovery_respects_smtp_boundary(flow, status, expected):
    db, _, _, _, mailer = flow
    row, service = queue(flow)
    row.status = status
    row.attempt_count = 1
    row.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()
    service.run_batch()
    assert row.status == expected
    assert len(mailer.messages) == (1 if status == 'processing' else 0)


def test_expired_or_revoked_access_link_rejected(flow):
    db, client, _, _, mailer = flow
    _, service = queue(flow)
    service.run_batch()
    token = re.search(r'\?token=([^\s]+)', mailer.messages[0]['body']).group(1)
    db.query(AgencyMemberAccessToken).one().expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.post('/api/agency-member/consume', json={'token': token}).status_code == 401


def test_tax_does_not_break_valid_unit_price(flow):
    db, client, txn, _, _ = flow
    txn['details']['totals']['total'] = '2916'
    assert webhook(client, txn).status_code == 200
    assert str(db.query(AgencyOrder).one().amount) == '29.16'


@pytest.mark.parametrize('case', ['price', 'quantity', 'recurring', 'currency', 'unpaid'])
def test_invalid_commercial_payload_rejected(flow, case):
    db, client, txn, _, _ = flow
    if case == 'price': txn['items'][0]['price']['unit_price']['amount'] = '1'
    if case == 'quantity': txn['items'][0]['quantity'] = 2
    if case == 'recurring': txn['items'][0]['price']['billing_cycle'] = {'interval': 'month', 'frequency': 1}
    if case == 'currency': txn['currency_code'] = 'EUR'
    if case == 'unpaid': txn['status'] = 'paid'
    assert webhook(client, txn).status_code == 400
    assert db.query(AgencyOrder).count() == 0


def test_smtp_config_failure_does_not_attempt_email(flow):
    db, _, _, _, mailer = flow
    row, service = queue(flow)
    mailer.config_missing = True
    service.run_batch()
    assert row.status == 'retry_wait'
    assert row.last_error == 'smtp_configuration_missing'
    assert db.query(AgencyMemberAccessToken).count() == 0
    assert not mailer.messages


def test_stale_worker_loses_send_fence(flow):
    db, _, _, provider, mailer = flow
    row, service = queue(flow)
    original = provider._api_request
    def simulate_new_claim(method, path):
        # Simulates the committed state left by another worker after lease recovery.
        row.attempt_count = 2
        db.commit()
        return original(method, path)
    provider._api_request = simulate_new_claim
    service.run_batch()
    assert row.attempt_count == 2 and not mailer.messages


def test_only_starter_entitlements_are_selected(flow):
    db, _, _, provider, mailer = flow
    row, service = queue(flow)
    db.query(AgencyEntitlement).one().product_key = 'pro-communications'
    db.commit()
    assert service.run_batch()['processed'] == 0
    assert not service.process_one(row.id)
    assert not provider.calls and not mailer.messages


def test_disabled_worker_does_not_open_database(monkeypatch):
    from app.services import agency_delivery_worker as worker
    monkeypatch.setattr(settings, 'AGENCY_STARTER_DELIVERY_ENABLED', False)
    monkeypatch.setattr(worker, 'SessionLocal', lambda: pytest.fail('unexpected database connection'))
    worker.run_delivery_tick()


def test_migration_round_trip_on_local_schema(flow):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    db, _, _, _, _ = flow
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/20260918_0004_agency_delivery_attempts.py'
    spec = importlib.util.spec_from_file_location('delivery_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with db.get_bind().begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        assert 'attempt_count' not in {c['name'] for c in inspect(connection).get_columns('agency_fulfilments')}
        migration.upgrade()
        names = {c['name'] for c in inspect(connection).get_columns('agency_fulfilments')}
        assert {'attempt_count', 'next_attempt_at', 'claimed_at', 'email_submitted_at'} <= names


def test_two_workers_only_one_smtp_attempt(flow, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _, _, txn, provider, mailer = flow
    engine = create_engine('sqlite:///' + str(tmp_path / 'workers.db'), connect_args={'check_same_thread': False})
    for model in (AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment, AgencyMemberAccessToken):
        model.__table__.create(engine)
    with Session(engine) as db:
        AgencyCommerceService(db).handle_completed_transaction(txn)
        identifier = db.query(AgencyFulfilment).one().id
    barrier = Barrier(2)
    def work():
        with Session(engine) as db:
            barrier.wait(timeout=5)
            return AgencyDeliveryService(db, provider, mailer).process_one(identifier)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(work) for _ in range(2)]
        assert sorted(f.result(timeout=10) for f in futures) == [False, True]
    assert len(mailer.messages) == 1
    engine.dispose()


def test_old_failure_cannot_overwrite_new_claim(flow):
    db, _, _, _, _ = flow
    row, service = queue(flow)
    row.status = 'processing'
    row.attempt_count = 2
    db.commit()
    service._failure(row.id, 'old_failure', True, expected_attempt=1)
    db.refresh(row)
    assert row.status == 'processing' and row.attempt_count == 2 and row.last_error is None


def test_revoked_access_link_and_inactive_customer_rejected(flow):
    db, client, _, _, mailer = flow
    _, service = queue(flow)
    service.run_batch()
    token = re.search(r'\?token=([^\s]+)', mailer.messages[0]['body']).group(1)
    record = db.query(AgencyMemberAccessToken).one()
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    assert client.post('/api/agency-member/consume', json={'token': token}).status_code == 401
    record.revoked_at = None
    db.query(AgencyCustomer).one().status = 'inactive'
    db.commit()
    assert client.post('/api/agency-member/consume', json={'token': token}).status_code == 401



def test_other_products_keep_existing_manual_delivery_identity(flow):
    db, client, txn, provider, mailer = flow
    txn['items'][0]['price']['id'] = 'pri_01m1a363nz4srjzs7qh7jk7zhw'
    txn['items'][0]['price']['unit_price']['amount'] = '6700'
    txn['details']['totals']['total'] = '6700'
    assert webhook(client, txn).status_code == 200
    assert db.query(AgencyCustomer).one().email == 'untrusted@example.com'
    assert AgencyDeliveryService(db, provider, mailer).run_batch()['processed'] == 0
    assert not mailer.messages
