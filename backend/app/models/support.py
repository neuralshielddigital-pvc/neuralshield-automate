from __future__ import annotations

from enum import Enum
from uuid import UUID

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupportTicketStatus(str, Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    CLOSED = "CLOSED"


class SupportTicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SupportTicket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "support_tickets"

    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SupportTicketStatus] = mapped_column(
        SQLEnum(SupportTicketStatus),
        default=SupportTicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[SupportTicketPriority] = mapped_column(
        SQLEnum(SupportTicketPriority),
        default=SupportTicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user = relationship("User")
