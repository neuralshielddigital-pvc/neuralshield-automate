from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.agency_commerce import (
    AgencyCustomer,
    AgencyEntitlement,
    AgencyFulfilment,
    AgencyOrder,
)
from app.models.enums import UserRole
from app.models.marketing import CampaignLead
from app.models.user import User
from app.schemas.agency_admin import (
    AgencyCustomerRead,
    AgencyEntitlementRead,
    AgencyFulfilmentRead,
    AgencyOrderRead,
)

router = APIRouter(prefix="/agency-admin", tags=["agency-admin"])


def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required.",
        )

    return current_user


@router.get("/overview")
def overview(
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> dict:
    customers = db.query(func.count(AgencyCustomer.id)).scalar() or 0
    orders = db.query(func.count(AgencyOrder.id)).scalar() or 0
    entitlements = (
        db.query(func.count(AgencyEntitlement.id)).scalar() or 0
    )
    fulfilments_pending = (
        db.query(func.count(AgencyFulfilment.id))
        .filter(
            AgencyFulfilment.status.in_(
                ["pending", "pending_customer_enrichment"]
            )
        )
        .scalar()
        or 0
    )

    revenue = (
        db.query(func.coalesce(func.sum(AgencyOrder.amount), 0))
        .filter(AgencyOrder.status == "completed")
        .scalar()
        or Decimal("0.00")
    )

    leads = (
        db.query(func.count(CampaignLead.id))
        .filter(CampaignLead.source == "agency-pilot")
        .scalar()
        or 0
    )

    return {
        "customers": int(customers),
        "orders": int(orders),
        "entitlements": int(entitlements),
        "pending_fulfilments": int(fulfilments_pending),
        "agency_leads": int(leads),
        "revenue_usd": str(revenue),
    }


@router.get("/customers", response_model=list[AgencyCustomerRead])
def customers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> list[AgencyCustomer]:
    return (
        db.query(AgencyCustomer)
        .order_by(AgencyCustomer.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/orders", response_model=list[AgencyOrderRead])
def orders(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> list[AgencyOrder]:
    return (
        db.query(AgencyOrder)
        .order_by(AgencyOrder.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get(
    "/entitlements",
    response_model=list[AgencyEntitlementRead],
)
def entitlements(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> list[AgencyEntitlement]:
    return (
        db.query(AgencyEntitlement)
        .order_by(AgencyEntitlement.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get(
    "/fulfilments",
    response_model=list[AgencyFulfilmentRead],
)
def fulfilments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> list[AgencyFulfilment]:
    return (
        db.query(AgencyFulfilment)
        .order_by(AgencyFulfilment.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/leads")
def leads(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    _: User = Depends(require_super_admin),
) -> list[dict]:
    rows = (
        db.query(CampaignLead)
        .filter(CampaignLead.source == "agency-pilot")
        .order_by(CampaignLead.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(row.id),
            "name": row.name,
            "email": row.email,
            "phone": row.phone,
            "source": row.source,
            "stage": row.stage.value if row.stage else None,
            "created_at": row.created_at,
        }
        for row in rows
    ]
