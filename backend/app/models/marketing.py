from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CampaignExecutionStatus, CampaignStatus, CampaignType, LeadStage

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "campaigns"

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
    type: Mapped[CampaignType] = mapped_column(
        Enum(CampaignType, name="campaign_type"),
        default=CampaignType.EMAIL,
        nullable=False,
        index=True,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        default=CampaignStatus.DRAFT,
        nullable=False,
        index=True,
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="campaigns")
    user: Mapped[User] = relationship("User", back_populates="campaigns")
    executions: Mapped[list[CampaignExecution]] = relationship(
        "CampaignExecution",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class Contact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "email", name="uq_contacts_user_id_email"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="contacts")


class CampaignLead(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "campaign_leads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_campaign_leads_tenant_id_email"),
    )

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
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    stage: Mapped[LeadStage] = mapped_column(
        Enum(LeadStage, name="lead_stage"),
        default=LeadStage.NEW,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="campaign_leads")
    user: Mapped[User] = relationship("User")
    executions: Mapped[list[CampaignExecution]] = relationship(
        "CampaignExecution",
        back_populates="lead",
        cascade="all, delete-orphan",
    )


class CampaignExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "campaign_executions"

    campaign_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("campaign_leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[CampaignExecutionStatus] = mapped_column(
        Enum(CampaignExecutionStatus, name="campaign_execution_status"),
        default=CampaignExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="executions")
    lead: Mapped[CampaignLead] = relationship("CampaignLead", back_populates="executions")
