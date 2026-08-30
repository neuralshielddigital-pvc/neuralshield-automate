from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.agency_resources.catalog import RESOURCE_ROOT
from app.api.deps import db_session
from app.models.agency_commerce import AgencyCustomer
from app.services.agency_member_service import (
    AgencyMemberService,
)


router = APIRouter(
    prefix="/agency-member",
    tags=["agency-member"],
)

member_bearer = HTTPBearer(auto_error=False)


class MemberAccessRequest(BaseModel):
    email: EmailStr


class MemberTokenConsumeRequest(BaseModel):
    token: str


def current_agency_member(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        member_bearer
    ),
    db: Session = Depends(db_session),
) -> AgencyCustomer:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Member authentication required.",
        )

    return AgencyMemberService(
        db
    ).authenticate_member_session(
        credentials.credentials
    )


@router.post("/request-access")
def request_access(
    payload: MemberAccessRequest,
    db: Session = Depends(db_session),
) -> dict:
    try:
        AgencyMemberService(db).request_access(
            payload.email
        )
    except Exception:
        # Keep public response non-enumerating.
        # Delivery failures remain server-side operational events.
        return {
            "accepted": True,
            "message": (
                "If this email has eligible Agency access, "
                "a secure link will be sent."
            ),
        }

    return {
        "accepted": True,
        "message": (
            "If this email has eligible Agency access, "
            "a secure link will be sent."
        ),
    }


@router.post("/consume")
def consume(
    payload: MemberTokenConsumeRequest,
    db: Session = Depends(db_session),
) -> dict:
    service = AgencyMemberService(db)

    customer, session_token = (
        service.consume_access_token(payload.token)
    )

    return {
        "member_token": session_token,
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
            for item in service.active_entitlements(
                customer.id
            )
        ],
        "resources": service.resources(customer.id),
    }


@router.get("/resources")
def list_resources(
    current_customer: AgencyCustomer = Depends(
        current_agency_member
    ),
    db: Session = Depends(db_session),
) -> dict:
    return {
        "items": AgencyMemberService(db).resources(
            current_customer.id
        )
    }


@router.get("/resources/{resource_id}")
def download_resource(
    resource_id: str,
    current_customer: AgencyCustomer = Depends(
        current_agency_member
    ),
    db: Session = Depends(db_session),
):
    item = AgencyMemberService(
        db
    ).resource_for_customer(
        current_customer.id,
        resource_id,
    )

    path = RESOURCE_ROOT / item["filename"]

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )

    return FileResponse(
        path=path,
        filename=item["filename"],
        media_type=item["media_type"],
    )
