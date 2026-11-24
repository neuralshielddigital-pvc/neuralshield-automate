from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.billing import SubscriptionResponse
from app.services.subscription_service import SubscriptionService
from app.core.config import settings
from app.schemas.billing import SubscriptionRead


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> SubscriptionResponse:
    subscription = SubscriptionService(db).get_current_subscription(current_user)
    if settings.AUTOMATION_WHOP_ENABLED and subscription and subscription.stripe_subscription_id.startswith("whop:"):
        from app.services.automation_whop_service import effective_membership
        from app.models.enums import SubscriptionStatus
        view = SubscriptionRead.model_validate(subscription)
        if effective_membership(db, current_user) is None:
            view = view.model_copy(update={"status": SubscriptionStatus.EXPIRED})
        return SubscriptionResponse(subscription=view)
    return SubscriptionResponse(subscription=subscription)
