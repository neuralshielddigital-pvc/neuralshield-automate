from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class AdminSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "admin_settings"

    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
