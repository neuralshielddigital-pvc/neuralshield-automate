import base64
import hashlib
import hmac

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.agency_commerce import AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment
from app.services.agency_whop_provider import WhopProvider, verify_signature
from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_persistence import AgencyWhopPersistence


def signed():
    sig = base64.b64encode(hmac.new(b'ws_synthetic', b'msg_test.1000.{}', hashlib.sha256).digest()).decode()
    return {'webhook-id': 'msg_test', 'webhook-timestamp': '1000', 'webhook-signature': 'v1,' + sig}


def test_signature_and_replay():
    verify_signature(b'{}', signed(), 'ws_synthetic', now=1000)
    for payload, now in [(b'{ }', 1000), (b'{}', 1301), (b'{}', 699)]:
        with pytest.raises(ValueError):
            verify_signature(payload, signed(), 'ws_synthetic', now=now)


def usd(value):
    return {'amount': value, 'currency': 'usd'}


def payment():
    return dict(id='pay_test', account_id='biz_test', status='paid', substatus='succeeded',
                billing_reason='one_time', currency='usd', product_id='prod_test', variant_id='plan_test',
                customer_email='buyer@example.com', subtotal=usd('27.00'), total=usd('29.70'),
                tax_amount=usd('2.70'), refunded_amount=usd('0'),
                line_items=[dict(product_id='prod_test', variant_id='plan_test', quantity=1, subtotal=usd('27.00'))])


def provider(monkeypatch, data):
    p = WhopProvider('synthetic', 'biz_test')
    variant = dict(id='plan_test', billing_type='one_time', account={'id': 'biz_test'}, product={'id': 'prod_test'})
    monkeypatch.setattr(p, 'retrieve', lambda resource, identifier: data if resource == 'payments' else variant)
    return p, variant


def test_paid_tax_and_refund(monkeypatch):
    data = payment()
    p, _ = provider(monkeypatch, data)
    facts, revoked = p.purchase('pay_test')
    assert facts.amount_usd == '27.00' and not revoked
    data['refunded_amount'] = usd('1')
    assert p.purchase('pay_test')[1]


@pytest.mark.parametrize('field,value', [('account_id', 'biz_other'), ('status', 'open'),
    ('billing_reason', 'subscription_cycle'), ('currency', 'eur'), ('total', usd('27.00')),
    ('subtotal', usd('NaN')), ('line_items', [])])
def test_rejects_invalid_purchase(monkeypatch, field, value):
    data = payment()
    data[field] = value
    p, _ = provider(monkeypatch, data)
    with pytest.raises(ValueError):
        p.purchase('pay_test')


def test_rejects_recurring_variant(monkeypatch):
    p, variant = provider(monkeypatch, payment())
    variant['billing_type'] = 'renewal'
    with pytest.raises(ValueError):
        p.purchase('pay_test')


@pytest.mark.parametrize('refund_first', [True, False])
def test_refund_cannot_be_reactivated(refund_first):
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine, tables=[c.__table__ for c in [AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment]])
    purchase = validate_verified_whop_purchase(independently_verified=True, payment_status='paid',
        provider_order_id='pay_test', provider_product_id='prod_test', configured_product_map={'prod_test': 'starter-toolkit'},
        amount='27.00', currency='USD', customer_email='buyer@example.com')
    with Session(engine) as db:
        service = AgencyWhopPersistence(db)
        if not refund_first:
            service.record_verified_purchase(purchase)
            assert db.query(AgencyEntitlement).one().status == 'active'
        service.record_verified_purchase(purchase, revoked=True)
        service.record_verified_purchase(purchase)
        assert db.query(AgencyOrder).one().status == 'revoked'
        assert db.query(AgencyEntitlement).one().status == 'revoked'
        assert db.query(AgencyFulfilment).one().status == 'revoked'
    engine.dispose()
