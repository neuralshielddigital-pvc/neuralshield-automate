from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.services.paddle_webhook_service as webhook_module
from app.core.config import settings
from app.models.billing import Payment, Subscription
from app.models.enums import SubscriptionStatus
from app.services.paddle_webhook_service import PaddleWebhookService


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, query_results=None):
        self.query_results = query_results or {}
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, model):
        return FakeQuery(self.query_results.get(model))

    def get(self, model, identifier):
        return self.query_results.get(("get", model, identifier))

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def signature_for(secret, timestamp, payload):
    digest = hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("utf-8") + b":" + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"ts={timestamp};h1={digest}"


def test_valid_paddle_signature(monkeypatch):
    timestamp = 1724150000
    payload = b'{"event_id":"evt_test"}'
    secret = "pdl_webhook_test_secret"

    monkeypatch.setattr(
        settings,
        "PADDLE_WEBHOOK_SECRET",
        secret,
    )
    monkeypatch.setattr(
        webhook_module.time,
        "time",
        lambda: timestamp,
    )

    service = PaddleWebhookService(FakeSession())
    service._verify_signature(
        payload,
        signature_for(secret, timestamp, payload),
    )


def test_invalid_paddle_signature(monkeypatch):
    timestamp = 1724150000

    monkeypatch.setattr(
        settings,
        "PADDLE_WEBHOOK_SECRET",
        "pdl_webhook_test_secret",
    )
    monkeypatch.setattr(
        webhook_module.time,
        "time",
        lambda: timestamp,
    )

    service = PaddleWebhookService(FakeSession())

    with pytest.raises(HTTPException) as exc_info:
        service._verify_signature(
            b'{"event_id":"evt_test"}',
            f"ts={timestamp};h1=invalid",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Invalid Paddle webhook signature."
    )


def test_expired_paddle_signature(monkeypatch):
    timestamp = 1724150000
    secret = "pdl_webhook_test_secret"
    payload = b'{"event_id":"evt_test"}'

    monkeypatch.setattr(
        settings,
        "PADDLE_WEBHOOK_SECRET",
        secret,
    )
    monkeypatch.setattr(
        webhook_module.time,
        "time",
        lambda: timestamp + 301,
    )

    service = PaddleWebhookService(FakeSession())

    with pytest.raises(HTTPException) as exc_info:
        service._verify_signature(
            payload,
            signature_for(secret, timestamp, payload),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == (
        "Paddle webhook signature has expired."
    )


def test_paddle_webhook_endpoint_with_mocked_service(
    client,
    monkeypatch,
):
    def fake_handle(self, payload, signature):
        assert json.loads(payload)["event_id"] == "evt_test"
        assert signature == "ts=1;h1=test"
        return {
            "received": True,
            "processed": True,
            "handled": True,
            "event_id": "paddle:evt_test",
            "event_type": "transaction.completed",
        }

    monkeypatch.setattr(
        PaddleWebhookService,
        "handle_webhook_event",
        fake_handle,
    )

    response = client.post(
        "/api/paddle/webhook",
        json={
            "event_id": "evt_test",
            "event_type": "transaction.completed",
        },
        headers={
            "Paddle-Signature": "ts=1;h1=test",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["handled"] is True
    assert response.json()["event_id"] == "paddle:evt_test"


def test_subscription_created_maps_to_local_subscription(
    monkeypatch,
):
    db = FakeSession({Subscription: None})
    service = PaddleWebhookService(db)

    user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
    )
    plan = SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        service,
        "_account_context",
        lambda data: (user, user.tenant_id),
    )
    monkeypatch.setattr(
        service,
        "_plan_from_event",
        lambda data: plan,
    )

    service._handle_subscription_event(
        "subscription.created",
        {
            "data": {
                "id": "sub_test",
                "customer_id": "ctm_test",
                "status": "active",
                "custom_data": {},
                "items": [{}],
                "current_billing_period": {
                    "starts_at": "2026-08-20T00:00:00Z",
                    "ends_at": "2026-09-20T00:00:00Z",
                },
                "scheduled_change": None,
            }
        },
    )

    assert len(db.added) == 1
    subscription = db.added[0]
    assert isinstance(subscription, Subscription)
    assert subscription.user_id == user.id
    assert subscription.tenant_id == user.tenant_id
    assert subscription.plan_id == plan.id
    assert subscription.stripe_customer_id == "paddle:ctm_test"
    assert subscription.stripe_subscription_id == "paddle:sub_test"
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.cancel_at_period_end is False


def test_transaction_completed_records_payment(
    monkeypatch,
):
    db = FakeSession({
        Payment: None,
        Subscription: None,
    })
    service = PaddleWebhookService(db)

    user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
    )
    plan = SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        service,
        "_account_context",
        lambda data: (user, user.tenant_id),
    )
    monkeypatch.setattr(
        service,
        "_plan_from_event",
        lambda data: plan,
    )

    service._handle_transaction_event(
        "transaction.completed",
        {
            "data": {
                "id": "txn_test",
                "subscription_id": "sub_test",
                "status": "completed",
                "currency_code": "USD",
                "custom_data": {},
                "items": [{}],
                "details": {
                    "totals": {
                        "grand_total": "5900",
                    }
                },
            }
        },
    )

    assert len(db.added) == 1
    payment = db.added[0]
    assert isinstance(payment, Payment)
    assert payment.user_id == user.id
    assert payment.tenant_id == user.tenant_id
    assert payment.plan_id == plan.id
    assert payment.provider == "paddle"
    assert (
        payment.provider_payment_id
        == "paddle:transaction:txn_test"
    )
    assert payment.provider_order_id == "paddle:sub_test"
    assert payment.amount == Decimal("59")
    assert payment.currency == "USD"
    assert payment.status == "paid"


def test_transaction_failed_marks_existing_subscription_incomplete(
    monkeypatch,
):
    user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
    )
    plan = SimpleNamespace(id=uuid4())
    subscription = SimpleNamespace(
        user_id=user.id,
        tenant_id=user.tenant_id,
        status=SubscriptionStatus.ACTIVE,
    )

    db = FakeSession({
        Payment: None,
        Subscription: subscription,
    })
    service = PaddleWebhookService(db)

    monkeypatch.setattr(
        service,
        "_account_context",
        lambda data: (user, user.tenant_id),
    )
    monkeypatch.setattr(
        service,
        "_plan_from_event",
        lambda data: plan,
    )

    service._handle_transaction_event(
        "transaction.payment_failed",
        {
            "data": {
                "id": "txn_failed",
                "subscription_id": "sub_test",
                "status": "past_due",
                "currency_code": "USD",
                "custom_data": {},
                "items": [{}],
                "details": {
                    "totals": {
                        "grand_total": "1900",
                    }
                },
            }
        },
    )

    assert len(db.added) == 1
    assert db.added[0].status == "failed"
    assert subscription.status == SubscriptionStatus.INCOMPLETE
