from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import CommissionStatus


class AffiliateRead(BaseModel):
    id: UUID
    user_id: UUID
    referral_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AffiliateMeResponse(BaseModel):
    is_registered: bool
    affiliate: AffiliateRead | None
    referral_link: str | None


class ReferralRead(BaseModel):
    id: UUID
    affiliate_id: UUID
    referred_user_id: UUID
    referred_user_email: EmailStr
    created_at: datetime


class CommissionRead(BaseModel):
    id: UUID
    affiliate_id: UUID
    referral_id: UUID
    amount: Decimal
    status: CommissionStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AffiliateStatsResponse(BaseModel):
    total_referrals: int
    pending_commissions: Decimal
    approved_commissions: Decimal
    paid_commissions: Decimal


class CommissionActionResponse(BaseModel):
    commission: CommissionRead
