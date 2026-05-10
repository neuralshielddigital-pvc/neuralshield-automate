from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.billing import Subscription
    from app.models.marketing import Campaign, CampaignLead
    from app.models.user import TenantUser, User
    from app.models.workflow import Workflow


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)

    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="tenant",
        foreign_keys="User.tenant_id",
    )
    tenant_users: Mapped[list[TenantUser]] = relationship(
        "TenantUser",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="tenant",
    )
    campaigns: Mapped[list[Campaign]] = relationship("Campaign", back_populates="tenant")
    campaign_leads: Mapped[list[CampaignLead]] = relationship("CampaignLead", back_populates="tenant")
    workflows: Mapped[list[Workflow]] = relationship("Workflow", back_populates="tenant")
