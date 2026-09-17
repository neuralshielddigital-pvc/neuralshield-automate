"""Sandbox harness tests use local SQL and injected fake providers only."""
import importlib.util
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agency_commerce import AgencyOrder, AgencyFulfilment
from app.services.agency_delivery_service import AgencyDeliveryService
from tests.test_agency_automatic_delivery import Provider, Mailer, webhook


@pytest.fixture
def harness(monkeypatch, agency_engine_factory):
    path = Path(__file__).resolve().parents[2] / 'ops/agency-provider-sandbox/sandbox_app.py'
    spec = importlib.util.spec_from_file_location('agency_sandbox_harness', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = dict(
        ENVIRONMENT='test',
        DATABASE_URL='postgresql+psycopg://agency_test:synthetic-test-only@agency-sandbox-db/nsd_agency_test_provider',
        PADDLE_ENVIRONMENT='sandbox', PADDLE_API_BASE_URL='https://sandbox-api.paddle.com',
        PADDLE_API_KEY='pdl_sdbx_apikey_synthetic',
        PADDLE_WEBHOOK_SECRET='synthetic-webhook-secret',
        AGENCY_STARTER_SANDBOX_PRICE_ID=module.PRICE,
        AGENCY_DELIVERY_TEST_RECIPIENT=module.RECIPIENT,
        AGENCY_MEMBER_BASE_URL=module.MEMBER_URL,
        AGENCY_STARTER_DELIVERY_ENABLED=True,
        SECRET_KEY='synthetic-sandbox-test-session-signing-secret',
        SMTP_HOST='smtp.example.invalid', SMTP_PORT=587, SMTP_USE_TLS=True,
        SMTP_FROM_EMAIL='sender@example.com', SMTP_USERNAME='', SMTP_PASSWORD='',
    )
    for key, value in config.items():
        monkeypatch.setattr(settings, key, value)
    monkeypatch.setenv('PADDLE_CLIENT_TOKEN', 'test_synthetic_client_token')
    with agency_engine_factory() as engine:
        yield module, engine


@pytest.mark.parametrize('key,value', [
    ('PADDLE_ENVIRONMENT', 'production'),
    ('DATABASE_URL', 'postgresql+psycopg://user:pass@production/nsd_agency_test_provider'),
    ('DATABASE_URL', 'postgresql+psycopg://agency_test:pass@agency-sandbox-db/neuralshield'),
    ('PADDLE_API_BASE_URL', 'https://api.paddle.com'),
    ('PADDLE_API_KEY', 'pdl_live_apikey_wrong'),
    ('AGENCY_MEMBER_BASE_URL', 'https://agency.neuralshielddigital.com/member/'),
    ('AGENCY_DELIVERY_TEST_RECIPIENT', 'other@example.com'),
    ('SMTP_USE_TLS', False),
    ('SMTP_PASSWORD', ''),
])
def test_unsafe_config_rejected_before_database(harness, monkeypatch, key, value):
    module, engine = harness
    if key == 'SMTP_PASSWORD':
        monkeypatch.setattr(settings, 'SMTP_USERNAME', 'synthetic-user')
    monkeypatch.setattr(settings, key, value)
    monkeypatch.setattr(module, 'create_engine', lambda *a, **k: pytest.fail('Database must not open'))
    with pytest.raises(ValueError):
        module.create_app(run_worker=False)


def test_unarmed_local_setup_has_no_checkout_or_webhook_processing(harness, monkeypatch):
    module, engine = harness
    monkeypatch.setattr(settings, 'AGENCY_STARTER_DELIVERY_ENABLED', False)
    monkeypatch.setattr(settings, 'PADDLE_API_KEY', '')
    monkeypatch.setenv('PADDLE_CLIENT_TOKEN', '')
    with TestClient(module.create_app(test_engine=engine, run_worker=False), base_url='http://localhost:8097') as client:
        assert client.get('/health').json()['armed'] is False
        assert client.get('/checkout-config').json()['clientToken'] == ''
        assert client.post('/api/paddle/webhook', content=b'{}').status_code == 503
        assert client.get('/').status_code == 200
        page = client.get('/member/')
        assert page.status_code == 200 and 'cdn.paddle.com' not in page.text
        assert page.headers['referrer-policy'] == 'no-referrer'
        assert client.post('/agency-member/request-access', json={'email': module.RECIPIENT}).status_code == 404
        assert client.get('/health', headers={'Host': 'evil.example'}).status_code == 400
        assert client.post('/agency-member/consume', headers={'Origin': 'https://evil.example'}, json={'token': 'x'}).status_code == 403


def test_sandbox_signed_order_to_member_download_and_single_order_cap(harness):
    import re
    module, engine = harness
    transaction = {
        'id': 'txn_' + uuid4().hex[:26], 'customer_id': 'ctm_' + uuid4().hex[:26],
        'status': 'completed', 'currency_code': 'USD',
        'items': [{'quantity': 1, 'price': {'id': module.PRICE,
                  'unit_price': {'amount': '2700', 'currency_code': 'USD'}, 'billing_cycle': None}}],
        'details': {'totals': {'total': '2700'}},
    }
    with TestClient(module.create_app(test_engine=engine, run_worker=False), base_url='http://localhost:8097') as client:
        assert client.get('/checkout-config').json()['ready'] is True
        assert webhook(client, transaction, signature_valid=False).status_code == 400
        assert webhook(client, transaction).status_code == 200
        assert webhook(client, transaction).json()['duplicate'] is True
        assert client.get('/checkout-config').json()['ready'] is False
        other = dict(transaction, id='txn_' + uuid4().hex[:26])
        assert webhook(client, other, 'evt_second_order').json()['reason'] == 'single_order_limit'
        with Session(engine) as db:
            assert db.query(AgencyOrder).count() == 1
            provider, mailer = Provider(transaction), Mailer()
            provider.customer['email'] = module.RECIPIENT
            assert AgencyDeliveryService(db, provider, mailer).run_batch()['processed'] == 1
            assert db.query(AgencyFulfilment).one().status == 'email_submitted'
            token = re.search(r'\?token=([^\s]+)', mailer.messages[0]['body']).group(1)
        consume = client.post('/agency-member/consume', json={'token': token})
        assert consume.status_code == 200
        result = client.get('/agency-member/resources/starter-download-pack', headers={
            'Authorization': 'Bearer ' + consume.json()['member_token']})
        assert result.status_code == 200 and result.content.startswith(b'PK')
        assert client.post('/agency-member/consume', json={'token': token}).status_code == 401
        assert len(mailer.messages) == 1


def test_wrong_price_is_ignored_without_dispatch_to_other_products(harness):
    module, engine = harness
    with TestClient(module.create_app(test_engine=engine, run_worker=False), base_url='http://localhost:8097') as client:
        response = webhook(client, {'items': [{'price': {'id': 'pri_' + 'x' * 26}}]})
        assert response.json() == {'received': True, 'handled': False}
        assert client.get('/health').json()['orders'] == 0
