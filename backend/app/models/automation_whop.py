"""Automation checkout ownership and paid periods, separate from legacy commerce."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AutomationWhopIntent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "automation_whop_intents"
    __table_args__ = (UniqueConstraint("user_id", "command_id", name="uq_automation_whop_command"),)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    command_id: Mapped[str] = mapped_column(String(36))
    plan_code: Mapped[str] = mapped_column(String(24))
    catalog_version: Mapped[str] = mapped_column(String(80))
    amount_minor: Mapped[int] = mapped_column(Integer)
    configuration_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class AutomationWhopMembership(Base, TimestampMixin):
    __tablename__ = "automation_whop_memberships"
    membership_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    intent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("automation_whop_intents.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), index=True)
    customer_id: Mapped[str] = mapped_column(String(255))
    plan_code: Mapped[str] = mapped_column(String(24))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AutomationWhopPayment(Base, TimestampMixin):
    __tablename__ = "automation_whop_payments"
    payment_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    membership_id: Mapped[str] = mapped_column(String(255), ForeignKey("automation_whop_memberships.membership_id", ondelete="RESTRICT"), index=True)
    intent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("automation_whop_intents.id", ondelete="RESTRICT"))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class AutomationWhopEvent(Base):
    __tablename__ = "automation_whop_events"
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    body_hash: Mapped[str] = mapped_column(String(64))
    handled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
