from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.agency_resources import (
    RESOURCE_CATALOG,
    resources_for_products,
)
from app.core.config import settings
from app.models.agency_commerce import (
    AgencyCustomer,
    AgencyEntitlement,
    AgencyFulfilment,
    AgencyMemberAccessToken,
)
from app.services.email_service import EmailService


class AgencyMemberService:
    TOKEN_TTL_MINUTES = 30
    SESSION_TTL_MINUTES = 60

    def __init__(self, db: Session) -> None:
        self.db = db

    def request_access(
        self,
        email: str,
    ) -> None:
        normalized = email.strip().lower()

        customer = (
            self.db.query(AgencyCustomer)
            .filter(AgencyCustomer.email == normalized)
            .first()
        )

        # Intentionally do nothing for non-customers.
        # Route response remains identical to prevent enumeration.
        if customer is None:
            return

        active_entitlement = (
            self.db.query(AgencyEntitlement)
            .filter(
                AgencyEntitlement.customer_id == customer.id,
                AgencyEntitlement.status == "active",
            )
            .first()
        )

        if active_entitlement is None:
            return

        raw_token = self._create_access_token(customer.id)

        access_url = (
            "https://agency.neuralshielddigital.com/member/"
            f"?token={quote(raw_token, safe='')}"
        )

        subject = "Your NeuralShield Agency member access link"
        body = (
            "Your secure NeuralShield Agency member access link is ready.\n\n"
            f"{access_url}\n\n"
            "This link expires in 30 minutes and can only be used once.\n\n"
            "If you did not request this link, you can ignore this email.\n\n"
            "NeuralShield Digital"
        )

        try:
            EmailService().send_email(
                to_email=normalized,
                subject=subject,
                body=body,
            )
        except Exception:
            self._revoke_raw_access_token(raw_token)
            raise

        now = datetime.now(timezone.utc)

        pending = (
            self.db.query(AgencyFulfilment)
            .join(
                AgencyEntitlement,
                AgencyFulfilment.entitlement_id
                == AgencyEntitlement.id,
            )
            .filter(
                AgencyEntitlement.customer_id == customer.id,
                AgencyFulfilment.status.in_(
                    [
                        "pending",
                        "pending_customer_enrichment",
                    ]
                ),
            )
            .all()
        )

        for fulfilment in pending:
            fulfilment.status = "delivered"
            fulfilment.destination = normalized
            fulfilment.delivered_at = now
            fulfilment.last_error = None

        self.db.commit()

    def _create_access_token(
        self,
        customer_id: UUID,
    ) -> str:
        raw_token = secrets.token_urlsafe(32)

        record = AgencyMemberAccessToken(
            customer_id=customer_id,
            token_hash=self._hash_token(raw_token),
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=self.TOKEN_TTL_MINUTES)
            ),
        )

        self.db.add(record)
        self.db.commit()

        return raw_token

    def _revoke_raw_access_token(
        self,
        raw_token: str,
    ) -> None:
        record = (
            self.db.query(AgencyMemberAccessToken)
            .filter(
                AgencyMemberAccessToken.token_hash
                == self._hash_token(raw_token)
            )
            .first()
        )

        if record is not None:
            record.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def consume_access_token(
        self,
        raw_token: str,
    ) -> tuple[AgencyCustomer, str]:
        token_hash = self._hash_token(raw_token)

        record = (
            self.db.query(AgencyMemberAccessToken)
            .filter(
                AgencyMemberAccessToken.token_hash == token_hash
            )
            .first()
        )

        now = datetime.now(timezone.utc)

        if (
            record is None
            or record.revoked_at is not None
            or record.used_at is not None
            or record.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Member access link is invalid or expired.",
            )

        customer = self.db.get(
            AgencyCustomer,
            record.customer_id,
        )

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Member access link is invalid or expired.",
            )

        record.used_at = now
        self.db.commit()

        session_token = self._create_member_session(
            customer.id
        )

        return customer, session_token

    def authenticate_member_session(
        self,
        raw_token: str,
    ) -> AgencyCustomer:
        try:
            payload = jwt.decode(
                raw_token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid member session.",
            ) from exc

        if payload.get("type") != "agency_member":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid member session.",
            )

        try:
            customer_id = UUID(str(payload.get("sub") or ""))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid member session.",
            ) from exc

        customer = self.db.get(
            AgencyCustomer,
            customer_id,
        )

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid member session.",
            )

        return customer

    def active_entitlements(
        self,
        customer_id: UUID,
    ) -> list[AgencyEntitlement]:
        return (
            self.db.query(AgencyEntitlement)
            .filter(
                AgencyEntitlement.customer_id == customer_id,
                AgencyEntitlement.status == "active",
            )
            .order_by(AgencyEntitlement.created_at.asc())
            .all()
        )

    def resources(
        self,
        customer_id: UUID,
    ) -> list[dict[str, Any]]:
        product_keys = {
            item.product_key
            for item in self.active_entitlements(customer_id)
        }

        return resources_for_products(product_keys)

    def resource_for_customer(
        self,
        customer_id: UUID,
        resource_id: str,
    ) -> dict[str, Any]:
        item = RESOURCE_CATALOG.get(resource_id)

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found.",
            )

        product_keys = {
            entitlement.product_key
            for entitlement
            in self.active_entitlements(customer_id)
        }

        if item["product_key"] not in product_keys:
            # Do not reveal existence of resources outside entitlement.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found.",
            )

        return item

    def _create_member_session(
        self,
        customer_id: UUID,
    ) -> str:
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(customer_id),
            "type": "agency_member",
            "iat": now,
            "exp": (
                now
                + timedelta(minutes=self.SESSION_TTL_MINUTES)
            ),
        }

        return jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()
