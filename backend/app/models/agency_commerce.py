from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgencyCustomer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agency_customers"

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        unique=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    agency_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
        index=True,
    )
    paddle_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
    )


class AgencyOrder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agency_orders"

    customer_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agency_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    paddle_transaction_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    paddle_price_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    product_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="completed",
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )


class AgencyEntitlement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agency_entitlements"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_key",
            name="uq_agency_entitlements_order_product",
        ),
    )

    customer_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agency_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agency_orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
    )
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class AgencyFulfilment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "agency_fulfilments"

    entitlement_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agency_entitlements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    delivery_method: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="member_portal",
    )
    destination: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
