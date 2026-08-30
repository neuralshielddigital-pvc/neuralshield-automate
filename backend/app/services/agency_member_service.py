from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agency_commerce import (
    AgencyCustomer,
    AgencyEntitlement,
    AgencyMemberAccessToken,
)


class AgencyMemberService:
    TOKEN_TTL_MINUTES = 30

    def __init__(self, db: Session) -> None:
        self.db = db

    def issue_access_token(
        self,
        email: str,
    ) -> str | None:
        normalized = email.strip().lower()

        customer = (
            self.db.query(AgencyCustomer)
            .filter(AgencyCustomer.email == normalized)
            .first()
        )

        # Do not disclose whether an email is a customer.
        if customer is None:
            return None

        active_entitlement = (
            self.db.query(AgencyEntitlement)
            .filter(
                AgencyEntitlement.customer_id == customer.id,
                AgencyEntitlement.status == "active",
            )
            .first()
        )

        if active_entitlement is None:
            return None

        raw_token = secrets.token_urlsafe(32)

        record = AgencyMemberAccessToken(
            customer_id=customer.id,
            token_hash=self._hash_token(raw_token),
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(minutes=self.TOKEN_TTL_MINUTES)
            ),
        )

        self.db.add(record)
        self.db.commit()

        return raw_token

    def consume_access_token(
        self,
        raw_token: str,
    ) -> AgencyCustomer:
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

        return customer

    def active_entitlements(
        self,
        customer_id,
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

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()
