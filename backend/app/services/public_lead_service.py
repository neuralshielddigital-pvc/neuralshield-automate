from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.marketing import CampaignLead
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.public import PublicLeadCreate, PublicLeadResponse
from app.services.lead_service import LeadService


class PublicLeadService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_public_lead(self, payload: PublicLeadCreate) -> PublicLeadResponse:
        tenant = self._find_tenant(payload.tenant_slug)
        owner = self._find_tenant_owner(tenant)
        email = str(payload.email).lower()

        existing_lead_id = self.db.scalar(
            select(CampaignLead.id).where(
                CampaignLead.tenant_id == tenant.id,
                CampaignLead.email == email,
            )
        )
        if existing_lead_id is not None:
            return self._safe_response()

        lead, _ = LeadService(self.db).upsert_lead(
            user_id=owner.id,
            tenant_id=tenant.id,
            name=payload.name,
            email=email,
            phone=payload.phone,
            source=payload.source or "website",
            tags=["public-form"],
            metadata={"message": payload.message},
        )
        self.db.commit()
        self.db.refresh(lead)
        LeadService(self.db)._fire_new_lead_trigger(owner, lead)
        return self._safe_response()

    def _find_tenant(self, tenant_slug: str) -> Tenant:
        normalized = self._normalize_slug(tenant_slug)
        tenant = self.db.scalar(
            select(Tenant).where(
                or_(
                    Tenant.slug == normalized,
                    Tenant.name.ilike(tenant_slug),
                    Tenant.name.ilike(tenant_slug.replace("-", " ")),
                )
            )
        )
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead form is not available.")
        return tenant

    def _find_tenant_owner(self, tenant: Tenant) -> User:
        owner = self.db.scalar(
            select(User)
            .where(User.tenant_id == tenant.id, User.is_active.is_(True))
            .order_by(User.created_at.asc())
        )
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead form is not available.")
        return owner

    def _normalize_slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower()).strip()

    def _safe_response(self) -> PublicLeadResponse:
        return PublicLeadResponse(success=True, message="Thanks. We received your request.")
