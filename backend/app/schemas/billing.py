from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlanInterval, SubscriptionStatus


class CheckoutSessionRequest(BaseModel):
    plan_name: str = Field(min_length=2, max_length=50)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingPortalSessionResponse(BaseModel):
    portal_url: str


class PlanRead(BaseModel):
    id: UUID
    name: str
    stripe_price_id: str
    price: Decimal
    interval: PlanInterval

    model_config = ConfigDict(from_attributes=True)


class SubscriptionRead(BaseModel):
    id: UUID
    stripe_customer_id: str
    stripe_subscription_id: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    plan: PlanRead

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    subscription: SubscriptionRead | None


class StripeWebhookResponse(BaseModel):
    received: bool
    processed: bool
    event_id: str | None = None
