from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agency_commerce import (
    AgencyCustomer,
    AgencyEntitlement,
    AgencyFulfilment,
    AgencyOrder,
)


AGENCY_PRICE_CATALOG: dict[str, dict[str, Any]] = {
    "pri_01kzx9mrs5g2bxgjgqwfcb4med": {
        "product_key": "starter-toolkit",
        "amount": Decimal("27.00"),
    },
    "pri_01m1a363nz4srjzs7qh7jk7zhw": {
        "product_key": "pro-communications",
        "amount": Decimal("67.00"),
    },
    "pri_01m1a37y66za25g2ahv2vqf0qy": {
        "product_key": "advanced-operations",
        "amount": Decimal("97.00"),
    },
    "pri_01m1a3a4j9d19nmcy54bfd8wgw": {
        "product_key": "agency-commercial-license",
        "amount": Decimal("197.00"),
    },
}


class AgencyCommerceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def is_agency_transaction(
        self,
        data: dict[str, Any],
    ) -> bool:
        return self._extract_agency_price(data) is not None

    def handle_completed_transaction(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        transaction_id = str(data.get("id") or "").strip()

        if not transaction_id.startswith("txn_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle transaction identifier is invalid.",
            )

        existing = (
            self.db.query(AgencyOrder)
            .filter(
                AgencyOrder.paddle_transaction_id == transaction_id
            )
            .first()
        )

        if existing is not None:
            return {
                "handled": True,
                "idempotent": True,
                "order_id": str(existing.id),
                "product_key": existing.product_key,
            }

        price_match = self._extract_agency_price(data)

        if price_match is None:
            return {
                "handled": False,
                "reason": "not_agency_price",
            }

        price_id, catalog = price_match

        paddle_customer_id = str(
            data.get("customer_id") or ""
        ).strip()

        if not paddle_customer_id.startswith("ctm_"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle customer identifier is invalid.",
            )

        customer_payload = data.get("customer") or {}
        custom_data = data.get("custom_data") or {}

        if not isinstance(customer_payload, dict):
            customer_payload = {}

        if not isinstance(custom_data, dict):
            custom_data = {}

        email = self._optional_email(
            customer_payload.get("email")
            or custom_data.get("email")
        )

        customer = (
            self.db.query(AgencyCustomer)
            .filter(
                AgencyCustomer.paddle_customer_id
                == paddle_customer_id
            )
            .first()
        )

        if customer is None and email:
            customer = (
                self.db.query(AgencyCustomer)
                .filter(AgencyCustomer.email == email)
                .first()
            )

        if customer is None:
            customer = AgencyCustomer(
                email=email,
                name=self._optional_string(
                    customer_payload.get("name")
                    or custom_data.get("name")
                ),
                agency_name=self._optional_string(
                    custom_data.get("agency_name")
                ),
                paddle_customer_id=paddle_customer_id,
                status="active",
            )
            self.db.add(customer)
            self.db.flush()
        else:
            if not customer.paddle_customer_id:
                customer.paddle_customer_id = paddle_customer_id

            if email and not customer.email:
                customer.email = email

        amount = self._extract_total_usd(data)

        if amount != catalog["amount"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle transaction amount mismatch.",
            )

        order = AgencyOrder(
            customer_id=customer.id,
            paddle_transaction_id=transaction_id,
            paddle_price_id=price_id,
            product_key=catalog["product_key"],
            amount=amount,
            currency="USD",
            status="completed",
            completed_at=self._parse_datetime(
                data.get("billed_at")
                or data.get("updated_at")
                or data.get("created_at")
            ),
        )
        self.db.add(order)
        self.db.flush()

        entitlement = AgencyEntitlement(
            customer_id=customer.id,
            order_id=order.id,
            product_key=catalog["product_key"],
            status="active",
            granted_at=datetime.now(timezone.utc),
        )
        self.db.add(entitlement)
        self.db.flush()

        fulfilment_status = (
            "pending"
            if customer.email
            else "pending_customer_enrichment"
        )

        fulfilment = AgencyFulfilment(
            entitlement_id=entitlement.id,
            status=fulfilment_status,
            delivery_method="member_portal",
            destination=customer.email,
        )
        self.db.add(fulfilment)

        self.db.commit()

        return {
            "handled": True,
            "idempotent": False,
            "order_id": str(order.id),
            "customer_id": str(customer.id),
            "entitlement_id": str(entitlement.id),
            "fulfilment_id": str(fulfilment.id),
            "product_key": catalog["product_key"],
            "customer_enrichment_required": customer.email is None,
        }

    def _extract_agency_price(
        self,
        data: dict[str, Any],
    ) -> tuple[str, dict[str, Any]] | None:
        items = data.get("items") or []

        if not isinstance(items, list):
            return None

        matches: list[tuple[str, dict[str, Any]]] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            price = item.get("price") or {}

            if not isinstance(price, dict):
                continue

            price_id = str(price.get("id") or "").strip()

            if price_id in AGENCY_PRICE_CATALOG:
                matches.append(
                    (price_id, AGENCY_PRICE_CATALOG[price_id])
                )

        if not matches:
            return None

        if len(matches) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Agency Paddle transaction must contain "
                    "exactly one Agency product."
                ),
            )

        return matches[0]

    def _extract_total_usd(
        self,
        data: dict[str, Any],
    ) -> Decimal:
        currency = str(
            data.get("currency_code") or ""
        ).strip().upper()

        if currency != "USD":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle transaction currency must be USD.",
            )

        details = data.get("details") or {}

        if not isinstance(details, dict):
            details = {}

        totals = details.get("totals") or {}

        if not isinstance(totals, dict):
            totals = {}

        raw_total = totals.get("total")

        if raw_total is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle transaction total is missing.",
            )

        try:
            return (
                Decimal(str(raw_total)) / Decimal("100")
            ).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agency Paddle transaction total is invalid.",
            ) from None

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_email(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip().lower()

        if not text or "@" not in text:
            return None

        return text

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if not value:
            return datetime.now(timezone.utc)

        text = str(value).replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return datetime.now(timezone.utc)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
