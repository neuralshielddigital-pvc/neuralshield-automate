import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    tenant_name: str = Field(min_length=2, max_length=150)
    ref: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_strong_password(cls, value: str) -> str:
        checks = [
            (r"[a-z]", "one lowercase letter"),
            (r"[A-Z]", "one uppercase letter"),
            (r"\d", "one number"),
            (r"[^A-Za-z0-9]", "one special character"),
        ]
        missing = [label for pattern, label in checks if re.search(pattern, value) is None]
        if missing:
            raise ValueError(f"Password must contain at least {', '.join(missing)}")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class AuthUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    role: UserRole
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(TokenResponse):
    user: AuthUserResponse
    tenant: AuthTenantResponse


class RefreshResponse(TokenResponse):
    pass


class MessageResponse(BaseModel):
    message: str
