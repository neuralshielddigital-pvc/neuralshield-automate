from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import WorkflowActionType, WorkflowRunStatus, WorkflowTriggerType


MAX_SYNC_WAIT_SECONDS = 30


class WorkflowActionCreate(BaseModel):
    type: WorkflowActionType
    config: dict[str, Any] = {}

    @model_validator(mode="after")
    def validate_config(self):
        if self.type == WorkflowActionType.SEND_WEBHOOK:
            url = str(self.config.get("url", ""))
            if not url:
                raise ValueError("SEND_WEBHOOK action requires config.url")
            if not url.startswith(("http://", "https://")):
                raise ValueError("SEND_WEBHOOK config.url must start with http:// or https://")

        if self.type == WorkflowActionType.SEND_EMAIL:
            missing = [k for k in ("to", "subject", "body") if not self.config.get(k)]
            if missing:
                raise ValueError(f"SEND_EMAIL action requires config fields: {', '.join(missing)}")

        if self.type == WorkflowActionType.ADD_AUDIT_LOG and not self.config.get("action"):
            raise ValueError("ADD_AUDIT_LOG action requires config.action")

        if self.type == WorkflowActionType.WAIT:
            seconds = self.config.get("seconds")

            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, int)
                or seconds < 1
                or seconds > MAX_SYNC_WAIT_SECONDS
            ):
                raise ValueError(
                    "WAIT action requires integer config.seconds "
                    f"between 1 and {MAX_SYNC_WAIT_SECONDS}."
                )

        if self.type == WorkflowActionType.CONDITION:
            explicit_condition = self.config.get("condition")

            if explicit_condition is not None:
                if not isinstance(explicit_condition, bool):
                    raise ValueError(
                        "CONDITION config.condition must be a boolean."
                    )
            else:
                has_left = "left" in self.config or "field" in self.config
                has_right = "right" in self.config or "value" in self.config
                operator = self.config.get("operator")

                if not has_left:
                    raise ValueError(
                        "CONDITION action requires config.left "
                        "or legacy config.field."
                    )

                if not operator:
                    raise ValueError(
                        "CONDITION action requires config.operator."
                    )

                if not has_right:
                    raise ValueError(
                        "CONDITION action requires config.right "
                        "or legacy config.value."
                    )

        return self


class WorkflowTriggerCreate(BaseModel):
    type: WorkflowTriggerType
    config: dict[str, Any] = {}


SUPPORTED_SCHEDULE_CRONS = {
    "0 */6 * * *",
    "0 */12 * * *",
    "0 0 * * *",
}


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    is_active: bool = False
    schedule_enabled: bool = False
    schedule_cron: str | None = None
    trigger: WorkflowTriggerCreate
    actions: list[WorkflowActionCreate]

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.trigger.type == WorkflowTriggerType.SCHEDULED:
            if not self.schedule_enabled:
                raise ValueError(
                    "Scheduled trigger requires schedule_enabled=true"
                )

            if self.schedule_cron not in SUPPORTED_SCHEDULE_CRONS:
                raise ValueError(
                    "Scheduled trigger requires a supported schedule."
                )
        else:
            self.schedule_enabled = False
            self.schedule_cron = None

        return self


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger: WorkflowTriggerCreate | None = None
    actions: list[WorkflowActionCreate] | None = None
    is_active: bool | None = None
    schedule_enabled: bool | None = None
    schedule_cron: str | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule_cron is not None:
            if self.schedule_cron not in SUPPORTED_SCHEDULE_CRONS:
                raise ValueError(
                    "Unsupported schedule. Use every 6 hours, "
                    "every 12 hours, or daily."
                )

        if self.schedule_enabled is True and not self.schedule_cron:
            raise ValueError(
                "schedule_cron is required when scheduling is enabled."
            )

        return self


class WorkflowActionRead(BaseModel):
    id: UUID
    workflow_id: UUID
    type: WorkflowActionType
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowTriggerRead(BaseModel):
    id: UUID
    workflow_id: UUID
    type: WorkflowTriggerType
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRead(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    is_active: bool
    schedule_enabled: bool
    schedule_cron: str | None = None
    next_run_at: datetime | None = None
    last_scheduled_run_at: datetime | None = None
    public_webhook_key: str
    triggers: list[WorkflowTriggerRead]
    actions: list[WorkflowActionRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class WorkflowListResponse(BaseModel):
    items: list[WorkflowRead]
    pagination: PaginationMeta


class WorkflowRunRead(BaseModel):
    id: UUID
    workflow_id: UUID
    status: WorkflowRunStatus
    logs: dict[str, Any] | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunRead]
    pagination: PaginationMeta


class PublicWorkflowWebhookResponse(BaseModel):
    message: str
    workflow_run_id: UUID | None = None
