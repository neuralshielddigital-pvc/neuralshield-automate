import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class PublicLeadCreate(BaseModel):
    tenant_slug: str = Field(min_length=2, max_length=160)
    name: str | None = Field(default=None, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default="website", max_length=120)
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if re.fullmatch(r"[0-9+\-\s()]{7,20}", value) is None:
            raise ValueError("Phone number must contain 7 to 20 valid phone characters.")
        return value


class AgencyPilotLeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    agency_name: str = Field(min_length=2, max_length=180)
    workflow: str = Field(min_length=10, max_length=2000)


class PublicLeadResponse(BaseModel):
    success: bool
    message: str
