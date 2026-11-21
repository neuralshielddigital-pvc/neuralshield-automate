"""Dedicated Whop SaaS tenant binding, isolated from Agency one-time orders.

A row may only be created by a future authenticated, explicitly authorized
subscription-claim flow. Webhooks must NEVER create or reassign a binding.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WhopSaasSubscriptionBinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "whop_saas_subscription_bindings"

    provider_subscription_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    provider_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    # No user receives access when the binding is first recorded.
    tier: Mapped[str] = mapped_column(String(32), default="unverified", nullable=False)
    access_state: Mapped[str] = mapped_column(String(32), default="inactive", nullable=False)
    access_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
