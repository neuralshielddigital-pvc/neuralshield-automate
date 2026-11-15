"""Route-level separation: signed SaaS renewals may not be acknowledged as Agency goods."""
import base64
import hashlib
import hmac
import json
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.api.routes.agency_whop import router
from app.core.config import settings
from app.services.agency_whop_provider import WhopRecurringPaymentPending


def signed_payment_request(client):
    body = json.dumps({
        "id": "msg_recurring_ci",
        "type": "payment.succeeded",
        "data": {"id": "pay_recurring_ci"},
    }).encode()
    timestamp = str(int(time.time()))
    signed = b"msg_recurring_ci." + timestamp.encode() + b"." + body
    signature = base64.b64encode(
        hmac.new(b"ws_synthetic", signed, hashlib.sha256).digest()
    ).decode()
    return client.post(
        "/webhooks/agency/whop",
        content=body,
        headers={
            "webhook-id": "msg_recurring_ci",
            "webhook-timestamp": timestamp,
            "webhook-signature": "v1," + signature,
        },
    )


def test_signed_recurring_payment_stays_retryable_without_grant(monkeypatch):
    monkeypatch.setattr(settings, "AGENCY_WHOP_ENABLED", True)
    monkeypatch.setattr(settings, "AGENCY_WHOP_ACCOUNT_ID", "biz_synthetic")
    monkeypatch.setattr(settings, "AGENCY_WHOP_WEBHOOK_SECRET", "ws_synthetic")
    monkeypatch.setattr(
        "app.api.routes.agency_whop.configured_agency_whop_products",
        lambda: {"prod_one_time": "starter-toolkit"},
    )
    calls = []

    def pending_purchase(self, payment_id):
        calls.append(payment_id)
        raise WhopRecurringPaymentPending("Recurring SaaS handler not ready")

    monkeypatch.setattr(
        "app.api.routes.agency_whop.WhopProvider.purchase", pending_purchase
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[db_session] = lambda: object()
    response = signed_payment_request(TestClient(app))
    assert response.status_code == 503
    assert response.json() == {"detail": "Retry delivery"}
    assert calls == ["pay_recurring_ci"]
