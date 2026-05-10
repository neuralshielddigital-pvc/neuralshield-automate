from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import WorkflowActionType, WorkflowRunStatus, WorkflowTriggerType
from app.schemas.campaign import PaginationMeta


class WorkflowTriggerCreate(BaseModel):
    type: WorkflowTriggerType
    config: dict = Field(default_factory=dict)


class WorkflowActionCreate(BaseModel):
    type: WorkflowActionType
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_config(self) -> "WorkflowActionCreate":
        if self.type == WorkflowActionType.SEND_WEBHOOK and not self.config.get("url"):
            raise ValueError("SEND_WEBHOOK action requires config.url")
        if self.type == WorkflowActionType.SEND_WEBHOOK and not str(self.config.get("url", "")).startswith(("http://", "https://")):
            raise ValueError("SEND_WEBHOOK config.url must start with http:// or https://")
        if self.type == WorkflowActionType.SEND_EMAIL:
            missing = [field for field in ("to", "subject", "body") if not self.config.get(field)]
            if missing:
                raise ValueError(f"SEND_EMAIL action requires config fields: {', '.join(missing)}")
        if self.type == WorkflowActionType.ADD_AUDIT_LOG and not self.config.get("action"):
            raise ValueError("ADD_AUDIT_LOG action requires config.action")
        return self


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    is_active: bool = False
    trigger: WorkflowTriggerCreate
    actions: list[WorkflowActionCreate] = Field(min_length=1, max_length=20)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    is_active: bool | None = None
    trigger: WorkflowTriggerCreate | None = None
    actions: list[WorkflowActionCreate] | None = Field(default=None, min_length=1, max_length=20)


class WorkflowTriggerRead(BaseModel):
    id: UUID
    workflow_id: UUID
    type: WorkflowTriggerType
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowActionRead(BaseModel):
    id: UUID
    workflow_id: UUID
    type: WorkflowActionType
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunRead(BaseModel):
    id: UUID
    workflow_id: UUID
    status: WorkflowRunStatus
    logs: dict
    trigger_payload: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    description: str | None
    is_active: bool
    public_webhook_key: str
    definition: dict
    triggers: list[WorkflowTriggerRead]
    actions: list[WorkflowActionRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowListResponse(BaseModel):
    items: list[WorkflowRead]
    pagination: PaginationMeta


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunRead]
    pagination: PaginationMeta


class PublicWorkflowWebhookResponse(BaseModel):
    workflow_id: UUID
    run_id: UUID
    status: WorkflowRunStatus
