from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.billing import Subscription
from app.models.user import User


class SubscriptionService:
    """Provider-neutral subscription query service."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_current_subscription(self, user: User) -> Subscription | None:
        return self.db.scalar(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.user_id == user.id,
                Subscription.tenant_id == user.tenant_id,
            )
            .order_by(Subscription.created_at.desc())
        )
