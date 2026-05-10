from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CampaignExecutionStatus, CampaignStatus, CampaignType, LeadStage


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    type: CampaignType = CampaignType.EMAIL
    subject: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=1)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    type: CampaignType | None = None
    status: CampaignStatus | None = None
    subject: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, min_length=1)


class CampaignRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    type: CampaignType
    status: CampaignStatus
    subject: str | None
    message: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignListResponse(BaseModel):
    items: list[CampaignRead]
    pagination: PaginationMeta


class LeadImportItem(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=120)
    stage: LeadStage = LeadStage.NEW
    notes: str | None = None
    last_contacted_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class LeadImportRequest(BaseModel):
    leads: list[LeadImportItem] = Field(min_length=1, max_length=1000)


class LeadRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str | None
    email: EmailStr
    phone: str | None
    source: str | None
    stage: LeadStage
    notes: str | None
    last_contacted_at: datetime | None
    tags: list[str]
    metadata_: dict = Field(serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LeadCreate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=120)
    stage: LeadStage = LeadStage.NEW
    notes: str | None = None
    last_contacted_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=120)
    stage: LeadStage | None = None
    notes: str | None = None
    last_contacted_at: datetime | None = None
    tags: list[str] | None = None
    metadata: dict | None = None


class LeadStageUpdate(BaseModel):
    stage: LeadStage


class LeadNotesUpdate(BaseModel):
    notes: str | None = None
    last_contacted_at: datetime | None = None


class LeadListResponse(BaseModel):
    items: list[LeadRead]
    pagination: PaginationMeta


class LeadImportResponse(BaseModel):
    imported: int
    updated: int
    items: list[LeadRead]


class CampaignExecutionRead(BaseModel):
    id: UUID
    campaign_id: UUID
    lead_id: UUID
    status: CampaignExecutionStatus
    executed_at: datetime | None
    response_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    is_active: bool = True
    definition: dict = Field(default_factory=dict)


class WorkflowRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    is_active: bool
    definition: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowListResponse(BaseModel):
    items: list[WorkflowRead]
    pagination: PaginationMeta


class CampaignStatsResponse(BaseModel):
    campaigns: int
    active_campaigns: int
    leads: int
    workflows: int
