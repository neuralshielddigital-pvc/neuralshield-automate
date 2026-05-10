from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import CampaignStatus, WorkflowTriggerType
from app.models.marketing import Campaign, CampaignLead
from app.models.user import User
from app.models.workflow import Workflow
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignStatsResponse,
    CampaignUpdate,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    PaginationMeta,
    WorkflowCreate,
    WorkflowListResponse,
)


def _pagination(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


class CampaignService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_campaign(self, user: User, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name=payload.name,
            type=payload.type,
            subject=payload.subject,
            message=payload.message,
            status=CampaignStatus.DRAFT,
        )
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def list_campaigns(self, user: User, page: int, page_size: int) -> CampaignListResponse:
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(Campaign).where(Campaign.tenant_id == user.tenant_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(Campaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return CampaignListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def get_campaign(self, user: User, campaign_id: UUID) -> Campaign:
        campaign = self.db.scalar(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.tenant_id == user.tenant_id)
        )
        if campaign is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
        return campaign

    def update_campaign(self, user: User, campaign_id: UUID, payload: CampaignUpdate) -> Campaign:
        campaign = self.get_campaign(user, campaign_id)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(campaign, field, value)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def delete_campaign(self, user: User, campaign_id: UUID) -> None:
        campaign = self.get_campaign(user, campaign_id)
        self.db.delete(campaign)
        self.db.commit()

    def activate_campaign(self, user: User, campaign_id: UUID) -> Campaign:
        campaign = self.get_campaign(user, campaign_id)
        campaign.status = CampaignStatus.ACTIVE
        self.db.commit()
        self.db.refresh(campaign)
        from app.services.workflow_service import WorkflowService

        WorkflowService(self.db).execute_tenant_trigger(
            user.tenant_id,
            WorkflowTriggerType.CAMPAIGN_ACTIVATED,
            {
                "campaign_id": str(campaign.id),
                "name": campaign.name,
                "type": campaign.type.value,
                "status": campaign.status.value,
                "subject": campaign.subject,
            },
        )
        return campaign

    def pause_campaign(self, user: User, campaign_id: UUID) -> Campaign:
        campaign = self.get_campaign(user, campaign_id)
        campaign.status = CampaignStatus.PAUSED
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def import_leads(self, user: User, payload: LeadImportRequest) -> LeadImportResponse:
        from app.services.lead_service import LeadService

        return LeadService(self.db).import_leads(user, payload)

    def list_leads(self, user: User, page: int, page_size: int) -> LeadListResponse:
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(CampaignLead).where(CampaignLead.tenant_id == user.tenant_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(CampaignLead.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return LeadListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def create_workflow(self, user: User, payload: WorkflowCreate) -> Workflow:
        workflow = Workflow(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name=payload.name,
            is_active=payload.is_active,
            definition=payload.definition,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def list_workflows(self, user: User, page: int, page_size: int) -> WorkflowListResponse:
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(Workflow).where(Workflow.tenant_id == user.tenant_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(Workflow.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return WorkflowListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def stats(self, user: User) -> CampaignStatsResponse:
        campaigns = self.db.scalar(select(func.count(Campaign.id)).where(Campaign.tenant_id == user.tenant_id)) or 0
        active = self.db.scalar(
            select(func.count(Campaign.id)).where(
                Campaign.tenant_id == user.tenant_id,
                Campaign.status == CampaignStatus.ACTIVE,
            )
        ) or 0
        leads = self.db.scalar(select(func.count(CampaignLead.id)).where(CampaignLead.tenant_id == user.tenant_id)) or 0
        workflows = self.db.scalar(select(func.count(Workflow.id)).where(Workflow.tenant_id == user.tenant_id)) or 0
        return CampaignStatsResponse(
            campaigns=int(campaigns),
            active_campaigns=int(active),
            leads=int(leads),
            workflows=int(workflows),
        )

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int]:
        return max(page, 1), min(max(page_size, 1), 100)
