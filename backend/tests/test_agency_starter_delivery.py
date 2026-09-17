"""Offline checks using synthetic purchases and an isolated in-memory database."""
from datetime import datetime, timedelta, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agency_resources.catalog import RESOURCE_CATALOG, RESOURCE_ROOT
from app.api.deps import db_session
from app.api.routes.agency_member import router
from app.core.config import settings
from app.models.agency_commerce import AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment
from app.services.agency_commerce_service import AgencyCommerceService
from app.services.agency_member_service import AgencyMemberService

ROOT = Path(__file__).resolve().parents[2]
PACK_ID = 'starter-download-pack'
PACK_NAME = 'NeuralShield_Agency_Starter_Toolkit_V1.zip'


@pytest.fixture
def delivery(monkeypatch):
    monkeypatch.setattr(settings, 'SECRET_KEY', 'synthetic-agency-delivery-tests-only-key')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    for model in (AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment):
        model.__table__.create(engine)
    with Session(engine) as db:
        app = FastAPI()
        app.include_router(router, prefix='/api')
        app.dependency_overrides[db_session] = lambda: db
        with TestClient(app) as client:
            yield db, client
    engine.dispose()


def purchase(db, price='pri_01kzx9mrs5g2bxgjgqwfcb4med', amount='2700'):
    unique = uuid4().hex
    result = AgencyCommerceService(db).handle_completed_transaction({
        'id': 'txn_synthetic_' + unique,
        'customer_id': 'ctm_synthetic_' + unique,
        'customer': {'email': unique + '@example.invalid'},
        'currency_code': 'USD',
        'items': [{'price': {'id': price}}],
        'details': {'totals': {'total': amount}},
    })
    customer = db.query(AgencyCustomer).filter_by(email=unique + '@example.invalid').one()
    token = AgencyMemberService(db)._create_member_session(customer.id)
    return result, customer, {'Authorization': 'Bearer ' + token}


def test_pack_matches_reviewed_source_bytes():
    manifest = json.loads((ROOT / 'docs/agency-starter-source-manifest.json').read_text())
    excluded = {row['name'] for row in manifest if 'Start_Here_Welcome' in row['name'] or 'TRN001_' in row['name']}
    expected = {row['name']: row['sha256'] for row in manifest if row['name'] not in excluded}
    assert len(expected) == 37
    with ZipFile(RESOURCE_ROOT / PACK_NAME) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'START_HERE.md', 'CONTENTS.txt'} | {'Templates/' + name for name in expected}
        for name, sha in expected.items():
            assert hashlib.sha256(archive.read('Templates/' + name)).hexdigest() == sha
        assert archive.read('START_HERE.md') == (RESOURCE_ROOT / 'starter-read-first.md').read_bytes()
        assert all(name in archive.read('CONTENTS.txt').decode() for name in expected)


def test_synthetic_completed_purchase_lists_and_downloads_pack(delivery):
    db, client = delivery
    result, _, auth = purchase(db)
    assert result['handled'] is True
    listed = client.get('/api/agency-member/resources', headers=auth)
    assert listed.status_code == 200
    items = listed.json()['items']
    assert PACK_ID in {item['id'] for item in items}
    assert {item['product_key'] for item in items} == {'starter-toolkit'}
    response = client.get('/api/agency-member/resources/' + PACK_ID, headers=auth)
    assert response.status_code == 200
    assert response.content == (RESOURCE_ROOT / PACK_NAME).read_bytes()
    assert response.headers['content-type'] == 'application/zip'
    assert PACK_NAME in response.headers['content-disposition']
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert ZipFile(BytesIO(response.content)).testzip() is None
    # Email dispatch remains a separate gap in the existing purchase handler.
    assert db.query(AgencyFulfilment).one().status == 'pending'


@pytest.mark.parametrize('auth', [{}, {'Authorization': 'Bearer invalid'}])
def test_unauthenticated_download_denied(delivery, auth):
    _, client = delivery
    assert client.get('/api/agency-member/resources/' + PACK_ID, headers=auth).status_code == 401


@pytest.mark.parametrize(('price', 'amount'), [
    ('pri_01m1a363nz4srjzs7qh7jk7zhw', '6700'),
    ('pri_01m1a37y66za25g2ahv2vqf0qy', '9700'),
    ('pri_01m1a3a4j9d19nmcy54bfd8wgw', '19700'),
])
def test_other_product_purchase_does_not_unlock_starter(delivery, price, amount):
    db, client = delivery
    purchase(db)
    _, _, auth = purchase(db, price, amount)
    assert PACK_ID not in {row['id'] for row in client.get('/api/agency-member/resources', headers=auth).json()['items']}
    assert client.get('/api/agency-member/resources/' + PACK_ID, headers=auth).status_code == 404


def test_revoked_entitlement_blocks_existing_session(delivery):
    db, client = delivery
    _, _, auth = purchase(db)
    db.query(AgencyEntitlement).one().status = 'revoked'
    db.commit()
    assert client.get('/api/agency-member/resources', headers=auth).json()['items'] == []
    assert client.get('/api/agency-member/resources/' + PACK_ID, headers=auth).status_code == 404


def test_expired_session_cannot_download(delivery):
    db, client = delivery
    _, customer, _ = purchase(db)
    token = jwt.encode({'sub': str(customer.id), 'type': 'agency_member', 'exp': datetime.now(timezone.utc) - timedelta(minutes=1)}, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert client.get('/api/agency-member/resources/' + PACK_ID, headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_missing_file_and_unknown_resource_return_404(delivery, monkeypatch):
    db, client = delivery
    _, _, auth = purchase(db)
    assert client.get('/api/agency-member/resources/no-such-resource', headers=auth).status_code == 404
    monkeypatch.setitem(RESOURCE_CATALOG[PACK_ID], 'filename', 'missing-test-pack.zip')
    assert client.get('/api/agency-member/resources/' + PACK_ID, headers=auth).status_code == 404


def test_existing_starter_templates_still_download(delivery):
    db, client = delivery
    _, _, auth = purchase(db)
    for resource in ('starter-client-intake', 'starter-discovery', 'starter-pipeline', 'starter-read-first'):
        assert client.get('/api/agency-member/resources/' + resource, headers=auth).status_code == 200
