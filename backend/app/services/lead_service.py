from __future__ import annotations

from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import LeadStage, WorkflowTriggerType
from app.models.marketing import CampaignLead
from app.models.user import User
from app.schemas.campaign import (
    LeadCreate,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadNotesUpdate,
    LeadStageUpdate,
    LeadUpdate,
    PaginationMeta,
)


def _pagination(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


class LeadService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_lead(self, user: User, payload: LeadCreate) -> CampaignLead:
        email = str(payload.email).lower()
        self._ensure_email_available(user, email)
        lead = CampaignLead(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name=payload.name,
            email=email,
            phone=payload.phone,
            source=payload.source,
            stage=payload.stage,
            notes=payload.notes,
            last_contacted_at=payload.last_contacted_at,
            tags=payload.tags,
            metadata_=payload.metadata,
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        self._fire_new_lead_trigger(user, lead)
        return lead

    def list_leads(self, user: User, page: int, page_size: int, search: str | None = None) -> LeadListResponse:
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(CampaignLead).where(CampaignLead.tenant_id == user.tenant_id)
        if search:
            term = f"%{search.strip()}%"
            base = base.where(
                or_(
                    CampaignLead.name.ilike(term),
                    CampaignLead.email.ilike(term),
                    CampaignLead.source.ilike(term),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(CampaignLead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return LeadListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def get_lead(self, user: User, lead_id: UUID) -> CampaignLead:
        lead = self.db.scalar(
            select(CampaignLead).where(CampaignLead.id == lead_id, CampaignLead.tenant_id == user.tenant_id)
        )
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
        return lead

    def update_lead(self, user: User, lead_id: UUID, payload: LeadUpdate) -> CampaignLead:
        lead = self.get_lead(user, lead_id)
        changes = payload.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] is not None:
            email = str(changes["email"]).lower()
            self._ensure_email_available(user, email, exclude_id=lead.id)
            lead.email = email
        for field in ("name", "phone", "source", "stage", "notes", "last_contacted_at", "tags"):
            if field in changes:
                setattr(lead, field, changes[field])
        if "metadata" in changes:
            lead.metadata_ = changes["metadata"] or {}
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_stage(self, user: User, lead_id: UUID, payload: LeadStageUpdate) -> CampaignLead:
        lead = self.get_lead(user, lead_id)
        lead.stage = payload.stage
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_notes(self, user: User, lead_id: UUID, payload: LeadNotesUpdate) -> CampaignLead:
        lead = self.get_lead(user, lead_id)
        lead.notes = payload.notes
        lead.last_contacted_at = payload.last_contacted_at
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete_lead(self, user: User, lead_id: UUID) -> None:
        lead = self.get_lead(user, lead_id)
        self.db.delete(lead)
        self.db.commit()

    def import_leads(self, user: User, payload: LeadImportRequest) -> LeadImportResponse:
        imported = 0
        updated = 0
        saved: list[CampaignLead] = []
        for item in payload.leads:
            lead, created = self.upsert_lead(
                user_id=user.id,
                tenant_id=user.tenant_id,
                name=item.name,
                email=str(item.email),
                phone=item.phone,
                source=item.source,
                stage=item.stage,
                notes=item.notes,
                last_contacted_at=item.last_contacted_at,
                tags=item.tags,
                metadata=item.metadata,
            )
            imported += 1 if created else 0
            updated += 0 if created else 1
            saved.append(lead)
        self.db.commit()
        for lead in saved:
            self.db.refresh(lead)
            self._fire_new_lead_trigger(user, lead)
        return LeadImportResponse(imported=imported, updated=updated, items=saved)

    def upsert_lead(
        self,
        user_id: UUID,
        tenant_id: UUID,
        name: str | None,
        email: str,
        phone: str | None = None,
        source: str | None = None,
        stage: LeadStage | None = None,
        notes: str | None = None,
        last_contacted_at=None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> tuple[CampaignLead, bool]:
        normalized_email = email.lower().strip()
        lead = self.db.scalar(
            select(CampaignLead).where(
                CampaignLead.tenant_id == tenant_id,
                CampaignLead.email == normalized_email,
            )
        )
        if lead is None:
            lead = CampaignLead(
                tenant_id=tenant_id,
                user_id=user_id,
                name=name,
                email=normalized_email,
                phone=phone,
                source=source,
                stage=stage or LeadStage.NEW,
                notes=notes,
                last_contacted_at=last_contacted_at,
                tags=tags or [],
                metadata_=metadata or {},
            )
            self.db.add(lead)
            self.db.flush()
            return lead, True
        lead.name = name
        lead.phone = phone
        lead.source = source
        if stage is not None:
            lead.stage = stage
        lead.notes = notes if notes is not None else lead.notes
        lead.last_contacted_at = last_contacted_at if last_contacted_at is not None else lead.last_contacted_at
        lead.tags = tags or []
        lead.metadata_ = metadata or {}
        self.db.flush()
        return lead, False

    def _ensure_email_available(self, user: User, email: str, exclude_id: UUID | None = None) -> None:
        query = select(CampaignLead.id).where(CampaignLead.tenant_id == user.tenant_id, CampaignLead.email == email)
        if exclude_id is not None:
            query = query.where(CampaignLead.id != exclude_id)
        if self.db.scalar(query) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lead email already exists for this tenant.")

    def _fire_new_lead_trigger(self, user: User, lead: CampaignLead) -> None:
        from app.services.workflow_service import WorkflowService

        WorkflowService(self.db).execute_tenant_trigger(
            user.tenant_id,
            WorkflowTriggerType.NEW_LEAD,
            {
                "lead_id": str(lead.id),
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "source": lead.source,
                "stage": lead.stage.value,
                "notes": lead.notes,
                "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
                "tags": lead.tags,
                "metadata": lead.metadata_,
            },
        )

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int]:
        return max(page, 1), min(max(page_size, 1), 100)
