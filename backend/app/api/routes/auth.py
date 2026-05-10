from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, login_rate_limit_ready
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
)
from app.schemas.user import CurrentUserRead
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(db_session)) -> AuthResponse:
    return AuthService(db).signup(payload)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    _: None = Depends(login_rate_limit_ready),
    db: Session = Depends(db_session),
) -> AuthResponse:
    return AuthService(db).login(payload)


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(db_session)) -> RefreshResponse:
    return AuthService(db).refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, db: Session = Depends(db_session)) -> MessageResponse:
    AuthService(db).logout(payload.refresh_token)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=CurrentUserRead)
def me(current_user: User = Depends(get_current_user)) -> CurrentUserRead:
    return CurrentUserRead(user=current_user, tenant=current_user.tenant)
