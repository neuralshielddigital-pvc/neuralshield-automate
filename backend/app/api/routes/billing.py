from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.billing import SubscriptionResponse
from app.services.subscription_service import SubscriptionService


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> SubscriptionResponse:
    subscription = SubscriptionService(db).get_current_subscription(current_user)
    return SubscriptionResponse(subscription=subscription)
