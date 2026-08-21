from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Plan, Subscription
from app.models.enums import SubscriptionStatus
from app.models.user import User


class PaddleService:
    PLAN_CONFIGURATION = {
        "starter": {
            "local_name": "Starter",
            "display_name": "Starter",
            "price": Decimal("19.00"),
            "price_setting": "PADDLE_STARTER_PRICE_ID",
        },
        "pro": {
            "local_name": "Pro",
            "display_name": "Pro",
            "price": Decimal("59.00"),
            "price_setting": "PADDLE_PRO_PRICE_ID",
        },
        "business": {
            "local_name": "Enterprise",
            "display_name": "Business",
            "price": Decimal("149.00"),
            "price_setting": "PADDLE_BUSINESS_PRICE_ID",
        },
        "enterprise": {
            "local_name": "Enterprise",
            "display_name": "Business",
            "price": Decimal("149.00"),
            "price_setting": "PADDLE_BUSINESS_PRICE_ID",
        },
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_transaction(
        self,
        user: User,
        plan_name: str,
    ) -> dict[str, str]:
        self._require_configuration()
        plan_config = self._plan_config(plan_name)
        plan = self._get_local_plan(plan_config["local_name"])

        if Decimal(plan.price) != plan_config["price"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Local billing plan price does not match approved pricing.",
            )

        active_subscription = (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user.id,
                Subscription.tenant_id == user.tenant_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.created_at.desc())
            .first()
        )

        if active_subscription is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An active subscription already exists. Contact support "
                    "to change plans without creating a duplicate subscription."
                ),
            )

        price_id = str(
            getattr(settings, plan_config["price_setting"])
        ).strip()

        self._validate_price(
            price_id,
            plan_config["price"],
        )

        response = self._api_request(
            "POST",
            "/transactions",
            {
                "items": [
                    {
                        "price_id": price_id,
                        "quantity": 1,
                    }
                ],
                "collection_mode": "automatic",
                "custom_data": {
                    "user_id": str(user.id),
                    "tenant_id": str(user.tenant_id),
                    "plan_id": str(plan.id),
                    "plan_name": plan.name,
                    "source": "neuralshield_automation",
                },
            },
        )

        transaction = response.get("data") or {}
        transaction_id = str(transaction.get("id") or "").strip()

        if not transaction_id.startswith("txn_"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Paddle returned an invalid transaction.",
            )

        return {
            "transaction_id": transaction_id,
            "provider": "paddle",
            "plan": plan_config["display_name"],
            "environment": settings.PADDLE_ENVIRONMENT,
        }

    def _validate_price(
        self,
        price_id: str,
        expected_price: Decimal,
    ) -> None:
        response = self._api_request("GET", f"/prices/{price_id}")
        price = response.get("data") or {}
        unit_price = price.get("unit_price") or {}
        billing_cycle = price.get("billing_cycle") or {}

        expected_amount = str(int(expected_price * Decimal("100")))

        if str(price.get("status") or "") != "active":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Selected Paddle price is not active.",
            )

        if str(unit_price.get("amount") or "") != expected_amount:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Paddle price does not match approved pricing.",
            )

        if str(unit_price.get("currency_code") or "") != "USD":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Paddle price currency must be USD.",
            )

        if (
            str(billing_cycle.get("interval") or "") != "month"
            or int(billing_cycle.get("frequency") or 0) != 1
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Paddle price must recur monthly.",
            )

    def _api_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = (
            json.dumps(payload).encode("utf-8")
            if payload is not None
            else None
        )
        base_url = settings.PADDLE_API_BASE_URL.rstrip("/")
        request = UrlRequest(
            f"{base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {settings.PADDLE_API_KEY}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=settings.REQUEST_TIMEOUT_SECONDS,
            ) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Paddle rejected the billing request.",
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Paddle billing is temporarily unavailable.",
            ) from exc

    def _require_configuration(self) -> None:
        required = {
            "PADDLE_API_KEY": settings.PADDLE_API_KEY,
            "PADDLE_API_BASE_URL": settings.PADDLE_API_BASE_URL,
            "PADDLE_STARTER_PRICE_ID": settings.PADDLE_STARTER_PRICE_ID,
            "PADDLE_PRO_PRICE_ID": settings.PADDLE_PRO_PRICE_ID,
            "PADDLE_BUSINESS_PRICE_ID": settings.PADDLE_BUSINESS_PRICE_ID,
        }

        missing = [
            name
            for name, value in required.items()
            if not str(value or "").strip()
        ]

        if missing:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Paddle billing configuration is incomplete.",
            )

        environment = str(settings.PADDLE_ENVIRONMENT).strip().lower()
        if environment != "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Paddle production billing is not enabled.",
            )

        if not str(settings.PADDLE_API_KEY).startswith("pdl_live_apikey_"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Paddle live API key is not configured.",
            )

    def _plan_config(self, plan_name: str) -> dict[str, Any]:
        normalized_name = str(plan_name or "").strip().lower()
        plan_config = self.PLAN_CONFIGURATION.get(normalized_name)

        if plan_config is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid billing plan.",
            )

        return plan_config

    def _get_local_plan(self, local_name: str) -> Plan:
        plan = (
            self.db.query(Plan)
            .filter(Plan.name == local_name)
            .order_by(Plan.created_at.desc())
            .first()
        )

        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Selected billing plan is unavailable.",
            )

        return plan
