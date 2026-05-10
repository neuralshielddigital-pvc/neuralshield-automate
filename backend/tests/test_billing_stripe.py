from __future__ import annotations

from app.services.stripe_service import StripeService


def test_stripe_checkout_session_creation_with_mocked_stripe(client, monkeypatch):
    monkeypatch.setattr(
        StripeService,
        "create_checkout_session",
        lambda self, user, plan_name: {"checkout_url": "https://checkout.stripe.test/session"},
    )

    response = client.post("/api/billing/create-checkout-session", json={"plan_name": "Pro"})

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://checkout.stripe.test/session"}


def test_stripe_webhook_subscription_sync_with_mocked_event(client, monkeypatch):
    def fake_handle(self, payload, signature):
        assert payload == b'{"id":"evt_test"}'
        assert signature == "test-signature"
        return {"received": True, "processed": True, "event_id": "evt_test"}

    monkeypatch.setattr(StripeService, "handle_webhook_event", fake_handle)

    response = client.post(
        "/api/stripe/webhook",
        content=b'{"id":"evt_test"}',
        headers={"stripe-signature": "test-signature", "content-type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["processed"] is True
