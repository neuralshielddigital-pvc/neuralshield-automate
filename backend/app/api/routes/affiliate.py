from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.affiliate import AffiliateMeResponse, AffiliateStatsResponse, CommissionRead, ReferralRead
from app.services.affiliate_service import AffiliateService


router = APIRouter(prefix="/affiliate", tags=["affiliate"])


@router.post("/register", response_model=AffiliateMeResponse, status_code=status.HTTP_201_CREATED)
def register_affiliate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> AffiliateMeResponse:
    return AffiliateService(db).register_affiliate(current_user)


@router.get("/me", response_model=AffiliateMeResponse)
def get_affiliate_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> AffiliateMeResponse:
    return AffiliateService(db).get_affiliate_me(current_user)


@router.get("/referrals", response_model=list[ReferralRead])
def get_affiliate_referrals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> list[ReferralRead]:
    return AffiliateService(db).get_referrals(current_user)


@router.get("/commissions", response_model=list[CommissionRead])
def get_affiliate_commissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> list[CommissionRead]:
    return AffiliateService(db).get_commissions(current_user)


@router.get("/stats", response_model=AffiliateStatsResponse)
def get_affiliate_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> AffiliateStatsResponse:
    return AffiliateService(db).get_stats(current_user)
