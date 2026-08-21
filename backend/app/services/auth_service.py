from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.security import AuditLog
from app.models.tenant import Tenant
from app.models.user import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    TenantUser,
    User,
)
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshResponse,
    SignupRequest,
)
from app.services.affiliate_service import AffiliateService
from app.services.email_service import EmailService


UTC = timezone.utc
logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def signup(self, payload: SignupRequest) -> AuthResponse:
        email = payload.email.lower()

        existing_user = self.db.scalar(
            select(User).where(User.email == email)
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        tenant = Tenant(
            name=payload.tenant_name,
            slug=self._unique_tenant_slug(payload.tenant_name),
        )
        self.db.add(tenant)
        self.db.flush()

        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            is_active=True,
            role=UserRole.ADMIN,
            tenant_id=tenant.id,
        )
        self.db.add(user)
        self.db.flush()

        tenant_user = TenantUser(
            user_id=user.id,
            tenant_id=tenant.id,
            role=UserRole.ADMIN,
        )
        self.db.add(tenant_user)

        raw_refresh_token = create_refresh_token()
        refresh_token = self._create_refresh_token_record(
            user,
            raw_refresh_token,
        )
        self.db.add(refresh_token)

        AffiliateService(self.db).create_referral_for_signup(
            payload.ref,
            user,
        )

        self._add_audit_log(
            user.id,
            "auth.signup",
            {"tenant_id": str(tenant.id)},
        )

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Signup could not be completed because "
                    "a unique value already exists."
                ),
            ) from exc

        self.db.refresh(user)
        self.db.refresh(tenant)

        # Verification email delivery must never roll back a successful signup.
        try:
            self.request_email_verification(user.email)
        except Exception:
            logger.exception(
                "Post-signup verification email setup failed for user_id=%s",
                user.id,
            )

        return self._auth_response(
            user,
            tenant,
            raw_refresh_token,
        )

    def login(self, payload: LoginRequest) -> AuthResponse:
        email = payload.email.lower()

        user = self.db.scalar(
            select(User).where(User.email == email)
        )

        if (
            user is None
            or not verify_password(
                payload.password,
                user.password_hash,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account is inactive.",
            )

        if user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Please verify your email address before signing in. "
                    "If you no longer have the verification email, "
                    "request a new verification link."
                ),
            )

        tenant = self.db.get(Tenant, user.tenant_id)

        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to a valid tenant.",
            )

        raw_refresh_token = create_refresh_token()

        refresh_token = self._create_refresh_token_record(
            user,
            raw_refresh_token,
        )

        self.db.add(refresh_token)

        self._add_audit_log(
            user.id,
            "auth.login",
            {"tenant_id": str(user.tenant_id)},
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(tenant)

        return self._auth_response(
            user,
            tenant,
            raw_refresh_token,
        )

    def refresh(
        self,
        raw_refresh_token: str,
    ) -> RefreshResponse:
        token_hash = hash_refresh_token(
            raw_refresh_token,
        )

        refresh_token = self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )

        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if (
            refresh_token.revoked
            or refresh_token.expires_at <= datetime.now(UTC)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is expired or revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.db.get(
            User,
            refresh_token.user_id,
        )

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is no longer valid.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        refresh_token.revoked = True

        new_raw_refresh_token = create_refresh_token()

        new_refresh_token = self._create_refresh_token_record(
            user,
            new_raw_refresh_token,
        )

        self.db.add(new_refresh_token)
        self.db.commit()

        return RefreshResponse(
            access_token=self._create_user_access_token(user),
            refresh_token=new_raw_refresh_token,
            expires_in=(
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
        )

    def logout(
        self,
        raw_refresh_token: str,
    ) -> None:
        token_hash = hash_refresh_token(
            raw_refresh_token,
        )

        refresh_token = self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )

        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refresh token was not found.",
            )

        refresh_token.revoked = True

        self._add_audit_log(
            refresh_token.user_id,
            "auth.logout",
            {},
        )

        self.db.commit()

    def request_email_verification(
        self,
        email: str,
    ) -> None:
        normalized_email = email.strip().lower()

        user = self.db.scalar(
            select(User).where(
                User.email == normalized_email
            )
        )

        # Generic silent behavior prevents account enumeration.
        if (
            user is None
            or not user.is_active
            or user.email_verified_at is not None
        ):
            return

        now = datetime.now(UTC)

        existing_tokens = self.db.scalars(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.revoked.is_(False),
            )
        ).all()

        for existing_token in existing_tokens:
            existing_token.revoked = True

        raw_token = secrets.token_urlsafe(48)

        verification_token = EmailVerificationToken(
            user_id=user.id,
            token_hash=self._hash_email_verification_token(
                raw_token
            ),
            expires_at=(
                now
                + timedelta(
                    hours=(
                        settings
                        .EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
                    )
                )
            ),
            used_at=None,
            revoked=False,
        )

        self.db.add(verification_token)

        self._add_audit_log(
            user.id,
            "auth.email_verification_requested",
            {
                "expires_in_hours": (
                    settings
                    .EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
                ),
            },
        )

        self.db.commit()

        verification_url = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"/verify-email?token="
            f"{quote(raw_token, safe='')}"
        )

        subject = "Verify your NeuralShieldDigital email"

        body = (
            "Welcome to NeuralShieldDigital.\n\n"
            "Please verify your email address to secure your account:\n"
            f"{verification_url}\n\n"
            "This verification link expires in "
            f"{settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours "
            "and can only be used once.\n\n"
            "If you did not create this account, "
            "you can safely ignore this email.\n\n"
            "NeuralShieldDigital Security"
        )

        try:
            EmailService().send_email(
                to_email=user.email,
                subject=subject,
                body=body,
            )
        except Exception:
            logger.exception(
                "Verification email could not be sent for user_id=%s",
                user.id,
            )

            verification_token.revoked = True

            self._add_audit_log(
                user.id,
                "auth.email_verification_delivery_failed",
                {},
            )

            self.db.commit()

    def verify_email(
        self,
        raw_token: str,
    ) -> None:
        token_hash = self._hash_email_verification_token(
            raw_token
        )

        verification_token = self.db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )

        now = datetime.now(UTC)

        if (
            verification_token is None
            or verification_token.revoked
            or verification_token.used_at is not None
            or verification_token.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Email verification token is invalid "
                    "or has expired."
                ),
            )

        user = self.db.get(
            User,
            verification_token.user_id,
        )

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Email verification token is invalid "
                    "or has expired."
                ),
            )

        if user.email_verified_at is None:
            user.email_verified_at = now

        verification_token.used_at = now
        verification_token.revoked = True

        other_tokens = self.db.scalars(
            select(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.id != verification_token.id,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.revoked.is_(False),
            )
        ).all()

        for other_token in other_tokens:
            other_token.revoked = True

        self._add_audit_log(
            user.id,
            "auth.email_verified",
            {},
        )

        self.db.commit()

    def request_password_reset(
        self,
        email: str,
    ) -> None:
        normalized_email = email.strip().lower()

        user = self.db.scalar(
            select(User).where(
                User.email == normalized_email
            )
        )

        # Always return silently for unknown/inactive accounts.
        # This prevents email-enumeration attacks.
        if user is None or not user.is_active:
            return

        now = datetime.now(UTC)

        existing_tokens = self.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked.is_(False),
            )
        ).all()

        for existing_token in existing_tokens:
            existing_token.revoked = True

        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_password_reset_token(
            raw_token,
        )

        token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=(
                now
                + timedelta(
                    minutes=(
                        settings
                        .PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
                    )
                )
            ),
            used_at=None,
            revoked=False,
        )

        self.db.add(token)

        self._add_audit_log(
            user.id,
            "auth.password_reset_requested",
            {
                "expires_in_minutes": (
                    settings
                    .PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
                ),
            },
        )

        self.db.commit()

        reset_url = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"/reset-password?token="
            f"{quote(raw_token, safe='')}"
        )

        subject = (
            "Reset your NeuralShieldDigital password"
        )

        body = (
            "We received a request to reset your "
            "NeuralShieldDigital password.\n\n"
            f"Reset your password:\n{reset_url}\n\n"
            f"This link expires in "
            f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} "
            "minutes and can only be used once.\n\n"
            "If you did not request this reset, "
            "you can safely ignore this email.\n\n"
            "NeuralShieldDigital Security"
        )

        try:
            EmailService().send_email(
                to_email=user.email,
                subject=subject,
                body=body,
            )
        except Exception:
            logger.exception(
                "Password reset email could not be sent "
                "for user_id=%s",
                user.id,
            )

            token.revoked = True

            self._add_audit_log(
                user.id,
                "auth.password_reset_email_failed",
                {},
            )

            self.db.commit()

    def reset_password(
        self,
        raw_token: str,
        new_password: str,
    ) -> None:
        token_hash = self._hash_password_reset_token(
            raw_token,
        )

        reset_token = self.db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )

        now = datetime.now(UTC)

        if (
            reset_token is None
            or reset_token.revoked
            or reset_token.used_at is not None
            or reset_token.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Password reset token is invalid "
                    "or has expired."
                ),
            )

        user = self.db.get(
            User,
            reset_token.user_id,
        )

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Password reset token is invalid "
                    "or has expired."
                ),
            )

        user.password_hash = hash_password(
            new_password,
        )

        reset_token.used_at = now
        reset_token.revoked = True

        other_reset_tokens = self.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.id != reset_token.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked.is_(False),
            )
        ).all()

        for other_token in other_reset_tokens:
            other_token.revoked = True

        refresh_tokens = self.db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
        ).all()

        for refresh_token in refresh_tokens:
            refresh_token.revoked = True

        self._add_audit_log(
            user.id,
            "auth.password_reset_completed",
            {
                "refresh_tokens_revoked": len(
                    refresh_tokens
                ),
            },
        )

        self.db.commit()

    def _create_refresh_token_record(
        self,
        user: User,
        raw_refresh_token: str,
    ) -> RefreshToken:
        expires_at = (
            datetime.now(UTC)
            + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        return RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(
                raw_refresh_token
            ),
            expires_at=expires_at,
            revoked=False,
        )

    def _create_user_access_token(
        self,
        user: User,
    ) -> str:
        return create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            additional_claims={
                "role": user.role.value,
            },
        )

    def _auth_response(
        self,
        user: User,
        tenant: Tenant,
        raw_refresh_token: str,
    ) -> AuthResponse:
        return AuthResponse(
            access_token=self._create_user_access_token(
                user
            ),
            refresh_token=raw_refresh_token,
            expires_in=(
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
            user=user,
            tenant=tenant,
        )

    def _add_audit_log(
        self,
        user_id,
        action: str,
        metadata: dict,
    ) -> None:
        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                metadata_=metadata,
            )
        )

    def _hash_email_verification_token(
        self,
        raw_token: str,
    ) -> str:
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

    def _hash_password_reset_token(
        self,
        raw_token: str,
    ) -> str:
        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

    def _unique_tenant_slug(
        self,
        name: str,
    ) -> str:
        base_slug = (
            re.sub(
                r"[^a-z0-9]+",
                "",
                name.lower(),
            ).strip()
            or "tenant"
        )

        slug = base_slug
        suffix = 2

        while (
            self.db.scalar(
                select(Tenant.id).where(
                    Tenant.slug == slug
                )
            )
            is not None
        ):
            slug = f"{base_slug}{suffix}"
            suffix += 1

        return slug
