from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.paddle_service import PaddleService


def test_paddle_checkout_endpoint_with_mocked_service(
    client,
    monkeypatch,
):
    def fake_create_transaction(self, user, plan_name):
        assert plan_name == "Pro"
        assert user.email == "admin@example.com"
        return {
            "transaction_id": "txn_test_neuralshield",
            "provider": "paddle",
            "plan": "Pro",
            "environment": "production",
        }

    monkeypatch.setattr(
        PaddleService,
        "create_transaction",
        fake_create_transaction,
    )

    response = client.post(
        "/api/paddle/checkout",
        json={"plan_name": "Pro"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "transaction_id": "txn_test_neuralshield",
        "provider": "paddle",
        "plan": "Pro",
        "environment": "production",
    }


@pytest.mark.parametrize(
    ("requested_name", "local_name", "display_name", "price"),
    [
        ("starter", "Starter", "Starter", Decimal("19.00")),
        ("PRO", "Pro", "Pro", Decimal("59.00")),
        ("business", "Enterprise", "Business", Decimal("149.00")),
        ("Enterprise", "Enterprise", "Business", Decimal("149.00")),
    ],
)
def test_paddle_locked_plan_configuration(
    requested_name,
    local_name,
    display_name,
    price,
):
    service = PaddleService(object())
    plan = service._plan_config(requested_name)

    assert plan["local_name"] == local_name
    assert plan["display_name"] == display_name
    assert plan["price"] == price


def test_paddle_rejects_unknown_plan():
    service = PaddleService(object())

    with pytest.raises(HTTPException) as exc_info:
        service._plan_config("unknown-plan")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid billing plan."


def test_paddle_validates_active_monthly_usd_price(monkeypatch):
    service = PaddleService(object())

    monkeypatch.setattr(
        service,
        "_api_request",
        lambda method, path: {
            "data": {
                "status": "active",
                "unit_price": {
                    "amount": "5900",
                    "currency_code": "USD",
                },
                "billing_cycle": {
                    "interval": "month",
                    "frequency": 1,
                },
            }
        },
    )

    service._validate_price(
        "pri_test_pro",
        Decimal("59.00"),
    )


def test_paddle_rejects_price_amount_mismatch(monkeypatch):
    service = PaddleService(object())

    monkeypatch.setattr(
        service,
        "_api_request",
        lambda method, path: {
            "data": {
                "status": "active",
                "unit_price": {
                    "amount": "1900",
                    "currency_code": "USD",
                },
                "billing_cycle": {
                    "interval": "month",
                    "frequency": 1,
                },
            }
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        service._validate_price(
            "pri_test_pro",
            Decimal("59.00"),
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == (
        "Paddle price does not match approved pricing."
    )
