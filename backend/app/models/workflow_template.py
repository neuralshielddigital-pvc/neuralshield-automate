from __future__ import annotations

from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class WorkflowTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_templates"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    definition: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    install_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(30), default="Beginner", nullable=False)
    estimated_setup_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
