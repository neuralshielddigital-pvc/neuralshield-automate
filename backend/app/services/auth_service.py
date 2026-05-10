import re
from datetime import UTC, datetime, timedelta

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
from app.models.user import RefreshToken, TenantUser, User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshResponse, SignupRequest
from app.services.affiliate_service import AffiliateService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def signup(self, payload: SignupRequest) -> AuthResponse:
        email = payload.email.lower()
        existing_user = self.db.scalar(select(User).where(User.email == email))
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        tenant = Tenant(name=payload.tenant_name, slug=self._unique_tenant_slug(payload.tenant_name))
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
        refresh_token = self._create_refresh_token_record(user, raw_refresh_token)
        self.db.add(refresh_token)
        AffiliateService(self.db).create_referral_for_signup(payload.ref, user)
        self._add_audit_log(user.id, "auth.signup", {"tenant_id": str(tenant.id)})

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Signup could not be completed because a unique value already exists.",
            ) from exc

        self.db.refresh(user)
        self.db.refresh(tenant)
        return self._auth_response(user, tenant, raw_refresh_token)

    def login(self, payload: LoginRequest) -> AuthResponse:
        email = payload.email.lower()
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None or not verify_password(payload.password, user.password_hash):
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

        tenant = self.db.get(Tenant, user.tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to a valid tenant.",
            )

        raw_refresh_token = create_refresh_token()
        refresh_token = self._create_refresh_token_record(user, raw_refresh_token)
        self.db.add(refresh_token)
        self._add_audit_log(user.id, "auth.login", {"tenant_id": str(user.tenant_id)})
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(tenant)
        return self._auth_response(user, tenant, raw_refresh_token)

    def refresh(self, raw_refresh_token: str) -> RefreshResponse:
        token_hash = hash_refresh_token(raw_refresh_token)
        refresh_token = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if refresh_token.revoked or refresh_token.expires_at <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is expired or revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.db.get(User, refresh_token.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is no longer valid.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        refresh_token.revoked = True
        new_raw_refresh_token = create_refresh_token()
        new_refresh_token = self._create_refresh_token_record(user, new_raw_refresh_token)
        self.db.add(new_refresh_token)
        self.db.commit()

        return RefreshResponse(
            access_token=self._create_user_access_token(user),
            refresh_token=new_raw_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        refresh_token = self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        if refresh_token is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refresh token was not found.",
            )

        refresh_token.revoked = True
        self._add_audit_log(refresh_token.user_id, "auth.logout", {})
        self.db.commit()

    def _create_refresh_token_record(self, user: User, raw_refresh_token: str) -> RefreshToken:
        expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=expires_at,
            revoked=False,
        )

    def _create_user_access_token(self, user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            tenant_id=str(user.tenant_id),
            additional_claims={"role": user.role.value},
        )

    def _auth_response(self, user: User, tenant: Tenant, raw_refresh_token: str) -> AuthResponse:
        return AuthResponse(
            access_token=self._create_user_access_token(user),
            refresh_token=raw_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
            tenant=tenant,
        )

    def _add_audit_log(self, user_id, action: str, metadata: dict) -> None:
        self.db.add(AuditLog(user_id=user_id, action=action, metadata_=metadata))

    def _unique_tenant_slug(self, name: str) -> str:
        base_slug = re.sub(r"[^a-z0-9]+", "", name.lower()).strip() or "tenant"
        slug = base_slug
        suffix = 2
        while self.db.scalar(select(Tenant.id).where(Tenant.slug == slug)) is not None:
            slug = f"{base_slug}{suffix}"
            suffix += 1
        return slug
