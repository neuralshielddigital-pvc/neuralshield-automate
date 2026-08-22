from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import (
    db_session,
    get_current_user,
    login_rate_limit_ready,
)
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    ResendVerificationEmailRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from app.schemas.user import CurrentUserRead
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: SignupRequest,
    db: Session = Depends(db_session),
) -> AuthResponse:
    return AuthService(db).signup(payload)


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    payload: LoginRequest,
    _: None = Depends(login_rate_limit_ready),
    db: Session = Depends(db_session),
) -> AuthResponse:
    return AuthService(db).login(payload)


@router.post(
    "/refresh",
    response_model=RefreshResponse,
)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(db_session),
) -> RefreshResponse:
    return AuthService(db).refresh(
        payload.refresh_token
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    payload: LogoutRequest,
    db: Session = Depends(db_session),
) -> MessageResponse:
    AuthService(db).logout(
        payload.refresh_token
    )

    return MessageResponse(
        message="Logged out successfully."
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    _: None = Depends(login_rate_limit_ready),
    db: Session = Depends(db_session),
) -> MessageResponse:
    AuthService(db).request_password_reset(
        str(payload.email)
    )

    return MessageResponse(
        message=(
            "If an account exists for that email, "
            "a password reset link has been sent."
        )
    )

@router.post(
    "/resend-verification-email",
    response_model=MessageResponse,
)
def resend_verification_email(
    payload: ResendVerificationEmailRequest,
    db: Session = Depends(db_session),
) -> MessageResponse:
    AuthService(db).request_email_verification(payload.email)

    return MessageResponse(
        message=(
            "If an account exists for that email, "
            "a verification email has been sent."
        )
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(db_session),
) -> MessageResponse:
    AuthService(db).verify_email(payload.token)

    return MessageResponse(
        message="Email verified successfully."
    )

@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(db_session),
) -> MessageResponse:
    AuthService(db).reset_password(
        payload.token,
        payload.new_password,
    )

    return MessageResponse(
        message=(
            "Password reset successfully. "
            "Please sign in with your new password."
        )
    )


@router.get(
    "/me",
    response_model=CurrentUserRead,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
) -> CurrentUserRead:
    return CurrentUserRead(
        user=current_user,
        tenant=current_user.tenant,
    )
