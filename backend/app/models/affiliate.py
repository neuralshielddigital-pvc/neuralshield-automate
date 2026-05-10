from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CommissionStatus

if TYPE_CHECKING:
    from app.models.user import User


class Affiliate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "affiliates"

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    referral_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    user: Mapped[User] = relationship("User", back_populates="affiliate_profile")
    referrals: Mapped[list[Referral]] = relationship(
        "Referral",
        back_populates="affiliate",
        cascade="all, delete-orphan",
    )
    commissions: Mapped[list[Commission]] = relationship(
        "Commission",
        back_populates="affiliate",
        cascade="all, delete-orphan",
    )


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint(
            "affiliate_id",
            "referred_user_id",
            name="uq_referrals_affiliate_id_referred_user_id",
        ),
    )

    affiliate_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("affiliates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    affiliate: Mapped[Affiliate] = relationship("Affiliate", back_populates="referrals")
    referred_user: Mapped[User] = relationship(
        "User",
        back_populates="referred_by_records",
        foreign_keys=[referred_user_id],
    )
    commissions: Mapped[list[Commission]] = relationship(
        "Commission",
        back_populates="referral",
        cascade="all, delete-orphan",
    )


class Commission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "commissions"

    affiliate_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("affiliates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referral_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[CommissionStatus] = mapped_column(
        Enum(CommissionStatus, name="commission_status"),
        default=CommissionStatus.PENDING,
        nullable=False,
        index=True,
    )

    affiliate: Mapped[Affiliate] = relationship("Affiliate", back_populates="commissions")
    referral: Mapped[Referral] = relationship("Referral", back_populates="commissions")
