from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class TenantRead(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    role: UserRole
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentUserRead(BaseModel):
    user: UserRead
    tenant: TenantRead
