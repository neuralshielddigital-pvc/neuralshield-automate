"""Signed recurring lifecycle events must not be silently acknowledged on activation."""
import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import db_session
from app.api.routes.agency_whop import router
from app.core.config import settings


@pytest.mark.parametrize("event_type", [
    "membership.activated",
    "membership.deactivated",
    "membership.cancel_at_period_end_changed",
    "membership.updated",
])
def test_signed_membership_event_is_retryable_when_saas_enabled(monkeypatch, event_type):
    monkeypatch.setattr(settings, "AGENCY_WHOP_ENABLED", True)
    monkeypatch.setattr(settings, "AGENCY_SAAS_WHOP_ENABLED", True)
    monkeypatch.setattr(settings, "AGENCY_WHOP_ACCOUNT_ID", "biz_synthetic")
    monkeypatch.setattr(settings, "AGENCY_WHOP_WEBHOOK_SECRET", "ws_synthetic")
    monkeypatch.setattr(
        "app.api.routes.agency_whop.configured_agency_whop_products",
        lambda: {"prod_one_time": "starter-toolkit"},
    )
    body = json.dumps({
        "id": "msg_membership_ci", "type": event_type,
        "data": {"id": "mem_synthetic"},
    }).encode()
    timestamp = str(int(time.time()))
    signed = b"msg_membership_ci." + timestamp.encode() + b"." + body
    signature = base64.b64encode(
        hmac.new(b"ws_synthetic", signed, hashlib.sha256).digest()
    ).decode()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[db_session] = lambda: object()
    response = TestClient(app).post(
        "/webhooks/agency/whop", content=body,
        headers={
            "webhook-id": "msg_membership_ci",
            "webhook-timestamp": timestamp,
            "webhook-signature": "v1," + signature,
        },
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Retry delivery"}
