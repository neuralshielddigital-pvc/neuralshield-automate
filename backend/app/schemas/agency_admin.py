from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AgencyCustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str | None
    agency_name: str | None
    paddle_customer_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class AgencyOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    paddle_transaction_id: str
    paddle_price_id: str
    product_key: str
    amount: Decimal
    currency: str
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgencyEntitlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    order_id: UUID
    product_key: str
    status: str
    granted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgencyFulfilmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entitlement_id: UUID
    status: str
    delivery_method: str
    destination: str | None
    delivered_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
