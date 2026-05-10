from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.affiliate import Affiliate, Commission, Referral
from app.models.enums import CommissionStatus
from app.models.user import User
from app.schemas.affiliate import (
    AffiliateMeResponse,
    AffiliateStatsResponse,
    CommissionActionResponse,
    CommissionRead,
    ReferralRead,
)


FRONTEND_SIGNUP_URL = "http://localhost:3000/signup"
DEFAULT_COMMISSION_RATE = Decimal("0.20")


class AffiliateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register_affiliate(self, user: User) -> AffiliateMeResponse:
        affiliate = self._get_affiliate_for_user(user.id)
        if affiliate is None:
            affiliate = Affiliate(
                user_id=user.id,
                referral_code=self._generate_unique_referral_code(user),
                is_active=True,
            )
            self.db.add(affiliate)
            try:
                self.db.commit()
            except IntegrityError as exc:
                self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Affiliate registration could not be completed. Please try again.",
                ) from exc
            self.db.refresh(affiliate)

        return self._affiliate_me_response(affiliate)

    def get_affiliate_me(self, user: User) -> AffiliateMeResponse:
        affiliate = self._get_affiliate_for_user(user.id)
        return self._affiliate_me_response(affiliate)

    def get_referrals(self, user: User) -> list[ReferralRead]:
        affiliate = self._require_affiliate(user)
        referrals = self.db.scalars(
            select(Referral)
            .options(joinedload(Referral.referred_user))
            .where(Referral.affiliate_id == affiliate.id)
            .order_by(Referral.created_at.desc())
        ).all()
        return [
            ReferralRead(
                id=referral.id,
                affiliate_id=referral.affiliate_id,
                referred_user_id=referral.referred_user_id,
                referred_user_email=referral.referred_user.email,
                created_at=referral.created_at,
            )
            for referral in referrals
        ]

    def get_commissions(self, user: User) -> list[Commission]:
        affiliate = self._require_affiliate(user)
        return list(
            self.db.scalars(
                select(Commission)
                .where(Commission.affiliate_id == affiliate.id)
                .order_by(Commission.created_at.desc())
            ).all()
        )

    def get_stats(self, user: User) -> AffiliateStatsResponse:
        affiliate = self._require_affiliate(user)
        total_referrals = self.db.scalar(
            select(func.count(Referral.id)).where(Referral.affiliate_id == affiliate.id)
        ) or 0

        sums = {
            status_value: self.db.scalar(
                select(func.coalesce(func.sum(Commission.amount), 0)).where(
                    Commission.affiliate_id == affiliate.id,
                    Commission.status == status_value,
                )
            )
            for status_value in [
                CommissionStatus.PENDING,
                CommissionStatus.APPROVED,
                CommissionStatus.PAID,
            ]
        }

        return AffiliateStatsResponse(
            total_referrals=int(total_referrals),
            pending_commissions=Decimal(sums[CommissionStatus.PENDING] or 0),
            approved_commissions=Decimal(sums[CommissionStatus.APPROVED] or 0),
            paid_commissions=Decimal(sums[CommissionStatus.PAID] or 0),
        )

    def create_referral_for_signup(self, referral_code: str | None, referred_user: User) -> None:
        if not referral_code:
            return

        affiliate = self.db.scalar(
            select(Affiliate).where(
                Affiliate.referral_code == referral_code.strip(),
                Affiliate.is_active.is_(True),
            )
        )
        if affiliate is None or affiliate.user_id == referred_user.id:
            return

        existing = self.db.scalar(
            select(Referral).where(
                Referral.affiliate_id == affiliate.id,
                Referral.referred_user_id == referred_user.id,
            )
        )
        if existing is not None:
            return

        self.db.add(Referral(affiliate_id=affiliate.id, referred_user_id=referred_user.id))

    def create_commission_for_active_subscription(self, referred_user: User, subscription_amount: Decimal) -> None:
        referral = self.db.scalar(
            select(Referral)
            .where(Referral.referred_user_id == referred_user.id)
            .order_by(Referral.created_at.asc())
        )
        if referral is None:
            return

        existing_commission = self.db.scalar(
            select(Commission).where(Commission.referral_id == referral.id)
        )
        if existing_commission is not None:
            return

        amount = (subscription_amount * DEFAULT_COMMISSION_RATE).quantize(Decimal("0.01"))
        self.db.add(
            Commission(
                affiliate_id=referral.affiliate_id,
                referral_id=referral.id,
                amount=amount,
                status=CommissionStatus.PENDING,
            )
        )

    def update_commission_status(self, commission_id, next_status: CommissionStatus) -> CommissionActionResponse:
        commission = self.db.get(Commission, commission_id)
        if commission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commission not found.",
            )
        commission.status = next_status
        self.db.commit()
        self.db.refresh(commission)
        return CommissionActionResponse(commission=CommissionRead.model_validate(commission))

    def _require_affiliate(self, user: User) -> Affiliate:
        affiliate = self._get_affiliate_for_user(user.id)
        if affiliate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User is not registered as an affiliate.",
            )
        return affiliate

    def _get_affiliate_for_user(self, user_id) -> Affiliate | None:
        return self.db.scalar(select(Affiliate).where(Affiliate.user_id == user_id))

    def _affiliate_me_response(self, affiliate: Affiliate | None) -> AffiliateMeResponse:
        if affiliate is None:
            return AffiliateMeResponse(is_registered=False, affiliate=None, referral_link=None)
        return AffiliateMeResponse(
            is_registered=True,
            affiliate=affiliate,
            referral_link=f"{FRONTEND_SIGNUP_URL}?ref={affiliate.referral_code}",
        )

    def _generate_unique_referral_code(self, user: User) -> str:
        email_prefix = user.email.split("@", 1)[0]
        cleaned_prefix = "".join(char for char in email_prefix.upper() if char.isalnum())[:8] or "AFF"
        for _ in range(10):
            candidate = f"{cleaned_prefix}-{uuid4().hex[:8].upper()}"
            exists = self.db.scalar(select(Affiliate.id).where(Affiliate.referral_code == candidate))
            if exists is None:
                return candidate
        return uuid4().hex[:12].upper()
