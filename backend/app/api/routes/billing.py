from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.billing import (
    BillingPortalSessionResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionResponse,
)
from app.services.stripe_service import StripeService


router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CheckoutSessionResponse:
    result = StripeService(db).create_checkout_session(current_user, payload.plan_name)
    return CheckoutSessionResponse(**result)


@router.post("/create-portal-session", response_model=BillingPortalSessionResponse)
def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> BillingPortalSessionResponse:
    result = StripeService(db).create_billing_portal_session(current_user)
    return BillingPortalSessionResponse(**result)


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> SubscriptionResponse:
    subscription = StripeService(db).get_current_subscription(current_user)
    return SubscriptionResponse(subscription=subscription)
