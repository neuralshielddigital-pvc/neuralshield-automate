from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.affiliate import Affiliate, Commission, Referral
    from app.models.billing import Subscription
    from app.models.marketing import Campaign, Contact
    from app.models.security import APIKey, AuditLog
    from app.models.tenant import Tenant
    from app.models.workflow import Workflow


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="users",
        foreign_keys=[tenant_id],
    )
    tenant_users: Mapped[list[TenantUser]] = relationship(
        "TenantUser",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_verification_tokens: Mapped[list[EmailVerificationToken]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="user",
    )
    affiliate_profile: Mapped[Affiliate | None] = relationship(
        "Affiliate",
        back_populates="user",
        uselist=False,
    )
    referred_by_records: Mapped[list[Referral]] = relationship(
        "Referral",
        back_populates="referred_user",
        foreign_keys="Referral.referred_user_id",
    )
    campaigns: Mapped[list[Campaign]] = relationship("Campaign", back_populates="user")
    contacts: Mapped[list[Contact]] = relationship("Contact", back_populates="user")
    workflows: Mapped[list[Workflow]] = relationship("Workflow", back_populates="user")
    api_keys: Mapped[list[APIKey]] = relationship("APIKey", back_populates="user")
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="user")


class TenantUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenant_users"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_tenant_users_user_id_tenant_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="tenant_user_role"),
        default=UserRole.USER,
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="tenant_users")
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="tenant_users")


class RefreshToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

class PasswordResetToken(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="password_reset_tokens",
    )

class EmailVerificationToken(
    Base,
    UUIDPrimaryKeyMixin,
    TimestampMixin,
):
    __tablename__ = "email_verification_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="email_verification_tokens",
    )
