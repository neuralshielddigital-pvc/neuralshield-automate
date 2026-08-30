from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.services.agency_member_service import (
    AgencyMemberService,
)


router = APIRouter(
    prefix="/agency-member",
    tags=["agency-member"],
)


class MemberAccessRequest(BaseModel):
    email: EmailStr


class MemberTokenConsumeRequest(BaseModel):
    token: str


@router.post("/request-access")
def request_access(
    payload: MemberAccessRequest,
    db: Session = Depends(db_session),
) -> dict:
    token = AgencyMemberService(db).issue_access_token(
        payload.email
    )

    # Delivery is added in the next slice.
    # Never disclose whether the email matched a customer.
    return {
        "accepted": True,
        "delivery_queued": token is not None,
    }


@router.post("/consume")
def consume(
    payload: MemberTokenConsumeRequest,
    db: Session = Depends(db_session),
) -> dict:
    service = AgencyMemberService(db)
    customer = service.consume_access_token(payload.token)

    entitlements = service.active_entitlements(customer.id)

    return {
        "customer": {
            "id": str(customer.id),
            "email": customer.email,
            "name": customer.name,
            "agency_name": customer.agency_name,
        },
        "entitlements": [
            {
                "id": str(item.id),
                "product_key": item.product_key,
                "status": item.status,
                "granted_at": item.granted_at,
            }
            for item in entitlements
        ],
    }
