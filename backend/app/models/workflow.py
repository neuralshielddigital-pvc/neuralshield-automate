from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkflowActionType, WorkflowRunStatus, WorkflowTriggerType

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class Workflow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflows"

    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    schedule_cron: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_scheduled_run_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_webhook_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="workflows")
    user: Mapped[User] = relationship("User", back_populates="workflows")
    triggers: Mapped[list[WorkflowTrigger]] = relationship(
        "WorkflowTrigger",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    actions: Mapped[list[WorkflowAction]] = relationship(
        "WorkflowAction",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list[WorkflowRun]] = relationship(
        "WorkflowRun",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )


class WorkflowTrigger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_triggers"

    workflow_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[WorkflowTriggerType] = mapped_column(
        Enum(WorkflowTriggerType, name="workflow_trigger_type"),
        nullable=False,
        index=True,
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="triggers")


class WorkflowAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_actions"

    workflow_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[WorkflowActionType] = mapped_column(
        Enum(WorkflowActionType, name="workflow_action_type"),
        nullable=False,
        index=True,
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="actions")


class WorkflowRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[WorkflowRunStatus] = mapped_column(
        Enum(WorkflowRunStatus, name="workflow_run_status"),
        default=WorkflowRunStatus.QUEUED,
        nullable=False,
        index=True,
    )
    logs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    trigger_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dead_letter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    workflow: Mapped[Workflow] = relationship("Workflow", back_populates="runs")
