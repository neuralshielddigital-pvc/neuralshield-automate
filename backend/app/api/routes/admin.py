from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.workflow_scheduler import run_due_scheduled_workflows
from app.services.gmail_poller import run_gmail_new_email_poll
from app.services.workflow_service import WorkflowService
from app.core.security import hash_password
from app.models.user import User
from app.models.enums import WorkflowRunStatus, UserRole
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_roles
from app.models.affiliate import Affiliate, Commission
from app.models.billing import Subscription, Payment, Payment
from app.models.enums import WorkflowRunStatus, CommissionStatus, SubscriptionStatus, UserRole
from app.models.marketing import CampaignLead
from app.models.security import APIKey, AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun
from app.schemas.affiliate import CommissionActionResponse
from app.services.affiliate_service import AffiliateService
from app.models.user import User
import os

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            )
        )
    ],
)

def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 25)))
    return page, page_size


def _pagination(page: int, page_size: int, total: int) -> dict:
    total = max(0, int(total or 0))
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }

def _tenant_name(db: Session, tenant_id):
    if not tenant_id:
        return None
    tenant = db.get(Tenant, tenant_id)
    return tenant.name if tenant else None



@router.get("/customers")
def customers(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = select(User).order_by(User.created_at.desc())
    if search:
        query = query.where(User.email.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    items = []
    for user in users:
        subscription = db.scalars(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.created_at.desc())
        ).first()

        payments = db.scalars(
            select(Payment)
            .where(Payment.user_id == user.id)
            .order_by(Payment.created_at.desc())
        ).all()

        last_payment = payments[0] if payments else None
        total_revenue = sum(
            float(payment.amount or 0)
            for payment in payments
            if str(payment.status).lower() in ("captured", "paid", "success", "succeeded")
        )

        affiliate = db.scalars(
            select(Affiliate).where(Affiliate.user_id == user.id)
        ).first()

        items.append({
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "tenant_name": _tenant_name(db, user.tenant_id),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "current_plan": subscription.plan.name if subscription and subscription.plan else None,
            "subscription_status": subscription.status.value if subscription and subscription.status else None,
            "current_period_end": subscription.current_period_end if subscription else None,
            "last_payment_amount": str(last_payment.amount) if last_payment else None,
            "last_payment_currency": last_payment.currency if last_payment else None,
            "last_payment_status": last_payment.status if last_payment else None,
            "last_payment_date": last_payment.created_at if last_payment else None,
            "total_revenue": str(total_revenue),
            "affiliate_referral_code": affiliate.referral_code if affiliate else None,
            "referred_by": None,
        })

    return {"items": items, "pagination": _pagination(page, page_size, int(total))}


@router.get("/customers/{user_id}")
def customer_detail(
    user_id: UUID,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    subscriptions = db.scalars(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).all()

    payments = db.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
    ).all()

    affiliate = db.scalars(select(Affiliate).where(Affiliate.user_id == user.id)).first()

    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(25)
    ).all()

    return {
        "user": {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value if user.role else None,
            "is_active": user.is_active,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "tenant_name": _tenant_name(db, user.tenant_id),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
        "subscriptions": [
            {
                "id": str(sub.id),
                "plan_name": sub.plan.name if sub.plan else None,
                "status": sub.status.value if sub.status else None,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created_at": sub.created_at,
            }
            for sub in subscriptions
        ],
        "payments": [
            {
                "id": str(payment.id),
                "provider": payment.provider,
                "provider_payment_id": payment.provider_payment_id,
                "provider_order_id": payment.provider_order_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "created_at": payment.created_at,
            }
            for payment in payments
        ],
        "affiliate": {
            "id": str(affiliate.id),
            "referral_code": affiliate.referral_code,
            "is_active": affiliate.is_active,
            "created_at": affiliate.created_at,
        } if affiliate else None,
        "audit_logs": [
            {
                "id": str(log.id),
                "action": log.action,
                "metadata": log.metadata_ or {},
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }



@router.get("/stats")
def admin_stats(
    db: Session = Depends(db_session),
) -> dict:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_subscriptions = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "ACTIVE")
    ) or 0
    total_leads = db.scalar(select(func.count(CampaignLead.id))) or 0
    workflows = db.scalar(select(func.count(Workflow.id))) or 0
    affiliate_commissions = db.scalar(select(func.coalesce(func.sum(Commission.amount), 0))) or 0
    return {
        "total_users": int(total_users),
        "active_subscriptions": int(active_subscriptions),
        "total_leads": int(total_leads),
        "workflows": int(workflows),
        "affiliate_commissions": str(affiliate_commissions),
    }


@router.get("/analytics")
def admin_analytics(
    db: Session = Depends(db_session),
) -> dict:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_30_days = now - timedelta(days=30)
    last_12_months = now - timedelta(days=365)

    paid_statuses = ("captured", "paid", "success", "succeeded")

    total_customers = db.scalar(select(func.count(User.id))) or 0
    active_subscriptions = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "ACTIVE")
    ) or 0
    cancelled_subscriptions = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "CANCELED")
    ) or 0
    total_affiliates = db.scalar(select(func.count(Affiliate.id))) or 0
    pending_commissions = db.scalar(
        select(func.coalesce(func.sum(Commission.amount), 0)).where(Commission.status == CommissionStatus.PENDING)
    ) or 0

    lifetime_revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(func.lower(Payment.status).in_(paid_statuses))
    ) or 0

    monthly_revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            func.lower(Payment.status).in_(paid_statuses),
            Payment.created_at >= month_start,
        )
    ) or 0

    revenue_30_days_rows = db.execute(
        select(
            func.date(Payment.created_at).label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .where(
            func.lower(Payment.status).in_(paid_statuses),
            Payment.created_at >= last_30_days,
        )
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
    ).all()

    revenue_12_months_rows = db.execute(
        select(
            func.to_char(func.date_trunc("month", Payment.created_at), "YYYY-MM").label("month"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        )
        .where(
            func.lower(Payment.status).in_(paid_statuses),
            Payment.created_at >= last_12_months,
        )
        .group_by(func.date_trunc("month", Payment.created_at))
        .order_by(func.date_trunc("month", Payment.created_at))
    ).all()

    plan_rows = db.execute(
        select(
            Subscription.status,
            func.count(Subscription.id),
        )
        .group_by(Subscription.status)
    ).all()

    plan_distribution_rows = db.execute(
        select(
            Subscription.plan_id,
            func.count(Subscription.id),
        )
        .where(Subscription.status == "ACTIVE")
        .group_by(Subscription.plan_id)
    ).all()

    return {
        "kpis": {
            "total_customers": int(total_customers),
            "active_subscriptions": int(active_subscriptions),
            "cancelled_subscriptions": int(cancelled_subscriptions),
            "monthly_revenue": str(monthly_revenue),
            "lifetime_revenue": str(lifetime_revenue),
            "total_affiliates": int(total_affiliates),
            "pending_commissions": str(pending_commissions),
        },
        "revenue_last_30_days": [
            {"date": str(row.day), "revenue": str(row.revenue)}
            for row in revenue_30_days_rows
        ],
        "revenue_last_12_months": [
            {"month": row.month, "revenue": str(row.revenue)}
            for row in revenue_12_months_rows
        ],
        "subscription_status": [
            {
                "status": row[0].value if row[0] else "UNKNOWN",
                "count": int(row[1] or 0),
            }
            for row in plan_rows
        ],
        "active_plan_distribution": [
            {
                "plan_id": str(row[0]) if row[0] else None,
                "count": int(row[1] or 0),
            }
            for row in plan_distribution_rows
        ],
    }







@router.post("/tenants/create")
def admin_create_tenant(
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    name = payload.get("name")
    slug = payload.get("slug")

    if not name or not slug:
        raise HTTPException(status_code=400, detail="Name and slug are required")

    existing = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")

    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return {
        "success": True,
        "tenant_id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
    }

@router.get("/tenants")
def admin_tenants(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = select(Tenant).order_by(Tenant.created_at.desc())
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Tenant.name.ilike(term), Tenant.slug.ilike(term)))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    tenants = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    paid_statuses = ("captured", "paid", "success", "succeeded")

    items = []
    for tenant in tenants:
        total_users = db.scalar(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        ) or 0

        active_users = db.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant.id,
                User.is_active == True,
            )
        ) or 0

        active_subscriptions = db.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.tenant_id == tenant.id,
                Subscription.status == "ACTIVE",
            )
        ) or 0

        total_revenue = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.tenant_id == tenant.id,
                func.lower(Payment.status).in_(paid_statuses),
            )
        ) or 0

        items.append({
            "tenant_id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "total_users": int(total_users),
            "active_users": int(active_users),
            "active_subscriptions": int(active_subscriptions),
            "total_revenue": str(total_revenue),
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
        })

    return {
        "items": items,
        "pagination": _pagination(page, page_size, total),
    }



@router.get("/tenants/{tenant_id}")
def admin_tenant_detail(
    tenant_id: UUID,
    db: Session = Depends(db_session),
) -> dict:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    paid_statuses = ("captured", "paid", "success", "succeeded")

    users = db.scalars(
        select(User)
        .where(User.tenant_id == tenant.id)
        .order_by(User.created_at.desc())
    ).all()

    subscriptions = db.scalars(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.tenant_id == tenant.id)
        .order_by(Subscription.created_at.desc())
    ).all()

    payments = db.scalars(
        select(Payment)
        .where(Payment.tenant_id == tenant.id)
        .order_by(Payment.created_at.desc())
    ).all()

    user_ids = [user.id for user in users]

    audit_logs = []
    if user_ids:
        audit_logs = db.scalars(
            select(AuditLog)
            .where(AuditLog.user_id.in_(user_ids))
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        ).all()

    total_revenue = sum(
        float(payment.amount or 0)
        for payment in payments
        if str(payment.status).lower() in paid_statuses
    )

    return {
        "tenant": {
            "tenant_id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
        },
        "summary": {
            "total_users": len(users),
            "active_users": len([user for user in users if user.is_active]),
            "active_subscriptions": len([
                subscription for subscription in subscriptions
                if subscription.status == SubscriptionStatus.ACTIVE
            ]),
            "total_revenue": str(total_revenue),
        },
        "users": [
            {
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role.value if user.role else None,
                "is_active": user.is_active,
                "created_at": user.created_at,
            }
            for user in users
        ],
        "subscriptions": [
            {
                "subscription_id": str(subscription.id),
                "user_id": str(subscription.user_id),
                "plan_name": subscription.plan.name if subscription.plan else None,
                "status": subscription.status.value if subscription.status else None,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "created_at": subscription.created_at,
            }
            for subscription in subscriptions
        ],
        "payments": [
            {
                "payment_id": str(payment.id),
                "user_id": str(payment.user_id),
                "provider": payment.provider,
                "provider_payment_id": payment.provider_payment_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "created_at": payment.created_at,
            }
            for payment in payments
        ],
        "audit_logs": [
            {
                "audit_log_id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "action": log.action,
                "metadata": log.metadata_ or {},
                "created_at": log.created_at,
            }
            for log in audit_logs
        ],
    }




@router.post("/users/create")
def create_admin_user(
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    email = payload.get("email")
    password = payload.get("password")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "USER")

    if not email or not password or not tenant_id:
        raise HTTPException(status_code=400, detail="Missing required fields")

    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        role_value = UserRole[role]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = User(
        email=email,
        password_hash=hash_password(password),
        tenant_id=tenant.id,
        role=role_value,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value if user.role else None,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }



@router.patch("/users/{user_id}/role")
def admin_update_user_role(
    user_id: UUID,
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = payload.get("role")
    if not role:
        raise HTTPException(status_code=400, detail="Role is required")

    try:
        role_value = UserRole[role]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = role_value
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value if user.role else None,
    }


@router.patch("/users/{user_id}/status")
def admin_update_user_status(
    user_id: UUID,
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_status = bool(payload.get("is_active", True))

    if new_status is False and user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.is_active == True,
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
            )
        ) or 0

        if active_admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot disable the last active admin")

    user.is_active = new_status
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "user_id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
    }


@router.get("/users")
def admin_users(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(User).order_by(User.created_at.desc())
    if search:
        query = query.where(User.email.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(user.id),
                "email": user.email,
                "is_active": user.is_active,
                "role": user.role.value,
                "tenant_id": str(user.tenant_id),
                "tenant_name": _tenant_name(db, user.tenant_id),
                "stripe_customer_id": user.stripe_customer_id,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
            for user in users
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/payments")
def admin_payments(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(Payment).options(
        selectinload(Payment.user),
        selectinload(Payment.plan),
    ).order_by(Payment.created_at.desc())

    if search:
        term = f"%{search.strip()}%"
        query = query.join(User).where(
            or_(
                User.email.ilike(term),
                Payment.provider.ilike(term),
                Payment.provider_payment_id.ilike(term),
                Payment.provider_order_id.ilike(term),
                Payment.status.ilike(term),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    payments = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "items": [
            {
                "id": str(payment.id),
                "user_id": str(payment.user_id),
                "user_email": payment.user.email if payment.user else None,
                "tenant_id": str(payment.tenant_id),
                "tenant_name": _tenant_name(db, payment.tenant_id),
                "plan_id": str(payment.plan_id) if payment.plan_id else None,
                "plan_name": payment.plan.name if payment.plan else None,
                "provider": payment.provider,
                "provider_payment_id": payment.provider_payment_id,
                "provider_order_id": payment.provider_order_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "created_at": payment.created_at,
            }
            for payment in payments
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }





@router.get("/customers/{user_id}/billing")
def admin_customer_billing(
    user_id: str,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payments = db.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
    ).all()

    subscriptions = db.scalars(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).all()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
        },
        "payments": [
            {
                "id": str(p.id),
                "provider": p.provider,
                "amount": str(p.amount),
                "currency": p.currency,
                "status": p.status,
                "payment_id": p.payment_id,
                "created_at": p.created_at,
            }
            for p in payments
        ],
        "subscriptions": [
            {
                "id": str(s.id),
                "plan": s.plan.name if s.plan else None,
                "status": s.status.value,
                "current_period_start": s.current_period_start,
                "current_period_end": s.current_period_end,
                "cancel_at_period_end": s.cancel_at_period_end,
                "created_at": s.created_at,
            }
            for s in subscriptions
        ],
    }

@router.get("/subscriptions")
def admin_subscriptions(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(Subscription).options(selectinload(Subscription.user), selectinload(Subscription.plan)).order_by(
        Subscription.created_at.desc()
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.join(User).where(or_(User.email.ilike(term), Subscription.stripe_customer_id.ilike(term)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    subscriptions = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(subscription.id),
                "user_email": subscription.user.email,
                "tenant_id": str(subscription.tenant_id),
                "tenant_name": _tenant_name(db, subscription.tenant_id),
                "plan_name": subscription.plan.name,
                "status": subscription.status.value,
                "stripe_customer_id": subscription.stripe_customer_id,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "created_at": subscription.created_at,
            }
            for subscription in subscriptions
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/leads")
def admin_leads(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(CampaignLead).order_by(CampaignLead.created_at.desc())
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(CampaignLead.name.ilike(term), CampaignLead.email.ilike(term), CampaignLead.source.ilike(term))
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    leads = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(lead.id),
                "tenant_id": str(lead.tenant_id),
                "tenant_name": _tenant_name(db, lead.tenant_id),
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "source": lead.source,
                "stage": lead.stage.value,
                "tags": lead.tags,
                "created_at": lead.created_at,
            }
            for lead in leads
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/workflows")
def admin_workflows(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(Workflow).order_by(Workflow.created_at.desc())
    if search:
        query = query.where(Workflow.name.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    workflows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(workflow.id),
                "tenant_id": str(workflow.tenant_id),
                "tenant_name": _tenant_name(db, workflow.tenant_id),
                "user_id": str(workflow.user_id),
                "name": workflow.name,
                "is_active": workflow.is_active,
                "created_at": workflow.created_at,
            }
            for workflow in workflows
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }

@router.get("/workflow-analytics")
def admin_workflow_analytics(
    db: Session = Depends(db_session),
) -> dict:
    workflows = db.scalars(
        select(Workflow).order_by(Workflow.created_at.desc())
    ).all()

    items = []

    for workflow in workflows:
        total_runs = db.scalar(
            select(func.count())
            .select_from(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow.id)
        ) or 0

        success_runs = db.scalar(
            select(func.count())
            .select_from(WorkflowRun)
            .where(
                WorkflowRun.workflow_id == workflow.id,
                WorkflowRun.status == WorkflowRunStatus.COMPLETED,
            )
        ) or 0

        failed_runs = db.scalar(
            select(func.count())
            .select_from(WorkflowRun)
            .where(
                WorkflowRun.workflow_id == workflow.id,
                WorkflowRun.status == WorkflowRunStatus.FAILED,
            )
        ) or 0

        last_run = db.scalar(
            select(WorkflowRun.created_at)
            .where(WorkflowRun.workflow_id == workflow.id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )

        success_rate = (
            round((success_runs / total_runs) * 100, 2)
            if total_runs > 0
            else 0
        )

        items.append({
            "workflow_id": str(workflow.id),
            "workflow_name": workflow.name,
            "total_runs": total_runs,
            "success_runs": success_runs,
            "failed_runs": failed_runs,
            "last_run": last_run,
            "success_rate": success_rate,
        })

    return {"items": items}
@router.get("/workflow-runs")
def admin_workflow_runs(
    page: int = 1,
    page_size: int = 25,
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = (
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.workflow))
        .order_by(WorkflowRun.created_at.desc())
    )

    if status:
        query = query.where(WorkflowRun.status == status)

    if search:
        term = f"%{search.strip()}%"
        query = query.join(Workflow).where(Workflow.name.ilike(term))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    runs = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "items": [
            {
                "id": str(run.id),
                "workflow_id": str(run.workflow_id),
                "workflow_name": run.workflow.name if run.workflow else None,
                "tenant_id": str(run.workflow.tenant_id) if run.workflow else None,
                "tenant_name": _tenant_name(db, run.workflow.tenant_id) if run.workflow else None,
                "status": run.status.value,
                "logs": run.logs,
                "retry_count": getattr(run, "retry_count", 0),
                "max_retries": getattr(run, "max_retries", 3),
                "next_retry_at": getattr(run, "next_retry_at", None),
                "last_error": getattr(run, "last_error", None),
                "is_dead_letter": getattr(run, "is_dead_letter", False),
                "created_at": run.created_at,
            }
            for run in runs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }

@router.get("/dead-letter")
def admin_dead_letter_queue(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = (
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.workflow))
        .where(WorkflowRun.is_dead_letter.is_(True))
        .order_by(WorkflowRun.created_at.desc())
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.join(Workflow).where(Workflow.name.ilike(term))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    runs = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "items": [
            {
                "id": str(run.id),
                "workflow_id": str(run.workflow_id),
                "workflow_name": run.workflow.name if run.workflow else None,
                "tenant_id": str(run.workflow.tenant_id) if run.workflow else None,
                "tenant_name": _tenant_name(db, run.workflow.tenant_id) if run.workflow else None,
                "status": run.status.value if run.status else None,
                "retry_count": getattr(run, "retry_count", 0),
                "max_retries": getattr(run, "max_retries", 3),
                "next_retry_at": getattr(run, "next_retry_at", None),
                "last_error": getattr(run, "last_error", None),
                "is_dead_letter": getattr(run, "is_dead_letter", False),
                "created_at": run.created_at,
                "updated_at": run.updated_at,
            }
            for run in runs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }

@router.get("/queue-dashboard")
def admin_queue_dashboard(
    db: Session = Depends(db_session),
) -> dict:
    queued = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.status == WorkflowRunStatus.QUEUED
        )
    ) or 0

    running = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.status == WorkflowRunStatus.RUNNING
        )
    ) or 0

    failed = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.status == WorkflowRunStatus.FAILED
        )
    ) or 0

    completed = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.status == WorkflowRunStatus.COMPLETED
        )
    ) or 0

    dead_letter = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.is_dead_letter.is_(True)
        )
    ) or 0

    retry_queue = db.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.next_retry_at.is_not(None)
        )
    ) or 0

    return {
        "queued": queued,
        "running": running,
        "failed": failed,
        "completed": completed,
        "dead_letter": dead_letter,
        "retry_queue": retry_queue,
        "worker": {
            "enabled": True,
            "interval_seconds": 60,
            "status": "running",
        },
    }

@router.get("/workflow-runs/{run_id}")
def admin_workflow_run_detail(
    run_id: str,
    db: Session = Depends(db_session),
):
    run = db.execute(
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.workflow))
        .where(WorkflowRun.id == run_id)
    ).scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    duration = None
    if run.created_at and run.updated_at:
        duration = int((run.updated_at - run.created_at).total_seconds())

    return {
        "id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "workflow_name": run.workflow.name if run.workflow else None,
        "status": run.status.value if run.status else None,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "duration_seconds": duration,
        "logs": getattr(run, "logs", None),
        "trigger_payload": getattr(run, "trigger_payload", None),
        "retry_count": getattr(run, "retry_count", 0),
        "max_retries": getattr(run, "max_retries", 3),
        "next_retry_at": getattr(run, "next_retry_at", None),
        "last_error": getattr(run, "last_error", None),
        "is_dead_letter": getattr(run, "is_dead_letter", False),
        "error_message": getattr(run, "last_error", None),
    }

@router.post("/workflow-runs/{run_id}/retry")
def admin_retry_workflow_run(
    run_id: str,
    payload_override: dict | None = Body(default=None),
    db: Session = Depends(db_session),
):
    old_run = db.execute(
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.workflow))
        .where(WorkflowRun.id == run_id)
    ).scalar_one_or_none()

    if not old_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if not old_run.workflow:
        raise HTTPException(status_code=404, detail="Workflow not found for this run")

    trigger_payload = getattr(old_run, "trigger_payload", None) or {}
    payload = payload_override or trigger_payload.get("payload") or {}

    class AdminWorkflowUser:
        id = old_run.workflow.user_id
        tenant_id = old_run.workflow.tenant_id


    new_run = WorkflowService(db).manual_run_workflow(
        AdminWorkflowUser(),
        old_run.workflow_id,
        payload,
    )

    old_run.is_dead_letter = True
    old_run.next_retry_at = None
    db.add(old_run)
    db.commit()

    return {
        "message": "Workflow retry started",
        "old_run_id": str(old_run.id),
        "new_run_id": str(new_run.id),
        "workflow_id": str(old_run.workflow_id),
        "status": new_run.status.value if new_run.status else None,
    }

@router.get("/affiliates")
def admin_affiliates(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(Affiliate).options(selectinload(Affiliate.user)).order_by(Affiliate.created_at.desc())
    if search:
        term = f"%{search.strip()}%"
        query = query.join(User).where(or_(Affiliate.referral_code.ilike(term), User.email.ilike(term)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    affiliates = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(affiliate.id),
                "user_id": str(affiliate.user_id),
                "user_email": affiliate.user.email,
                "referral_code": affiliate.referral_code,
                "is_active": affiliate.is_active,
                "created_at": affiliate.created_at,
            }
            for affiliate in affiliates
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/commissions")
def admin_commissions(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(Commission).options(selectinload(Commission.affiliate)).order_by(Commission.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    commissions = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(commission.id),
                "affiliate_id": str(commission.affiliate_id),
                "referral_id": str(commission.referral_id),
                "referral_code": commission.affiliate.referral_code if commission.affiliate else None,
                "amount": str(commission.amount),
                "status": commission.status.value,
                "created_at": commission.created_at,
                "updated_at": commission.updated_at,
            }
            for commission in commissions
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/audit-logs")
def admin_audit_logs(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(AuditLog).options(selectinload(AuditLog.user)).order_by(AuditLog.created_at.desc())
    if search:
        query = query.where(AuditLog.action.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    logs = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user.email if log.user else None,
                "action": log.action,
                "metadata": log.metadata_,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }

@router.get("/security-events")
def admin_security_events(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    security_actions = [
        "login_failed",
        "login_success",
        "password_reset",
        "suspicious_activity",
        "api_key_created",
        "api_key_deleted",
        "token_revoked",
    ]

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.action.in_(security_actions))
        .order_by(AuditLog.created_at.desc())
    )

    total = db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    logs = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user.email if log.user else None,
                "action": log.action,
                "metadata": log.metadata_,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }

@router.post("/commissions/{commission_id}/approve", response_model=CommissionActionResponse)
def approve_commission(
    commission_id: UUID,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.APPROVED)


@router.post("/commissions/{commission_id}/reject", response_model=CommissionActionResponse)
def reject_commission(
    commission_id: UUID,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.REJECTED)


@router.post("/commissions/{commission_id}/mark-paid", response_model=CommissionActionResponse)
def mark_commission_paid(
    commission_id: UUID,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.PAID)



@router.get("/revenue")
def admin_revenue(
    db: Session = Depends(db_session),
) -> dict:
    payments = db.execute(select(Payment)).scalars().all()
    subscriptions = db.execute(select(Subscription)).scalars().all()
    users = db.execute(select(User)).scalars().all()

    total_revenue = sum(float(p.amount or 0) for p in payments if str(p.status).lower() in ("captured", "paid", "success", "succeeded"))
    active_subscriptions = len([s for s in subscriptions if str(s.status).upper() == "ACTIVE"])

    return {
        "currency": "INR",
        "total_revenue": total_revenue,
        "monthly_revenue": total_revenue,
        "active_subscriptions": active_subscriptions,
        "total_customers": len(users),
    }


@router.patch("/subscriptions/{subscription_id}/cancel")
def cancel_subscription(
    subscription_id: str,
    db: Session = Depends(db_session),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.status = "CANCELED"
    subscription.cancel_at_period_end = True
    db.commit()
    db.refresh(subscription)

    return {"success": True, "status": subscription.status}


@router.patch("/subscriptions/{subscription_id}/pause")
def pause_subscription(
    subscription_id: str,
    db: Session = Depends(db_session),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.status = "PAUSED"
    db.commit()
    db.refresh(subscription)

    return {"success": True, "status": subscription.status}


@router.patch("/subscriptions/{subscription_id}/reactivate")
def reactivate_subscription(
    subscription_id: str,
    db: Session = Depends(db_session),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.status = "ACTIVE"
    subscription.cancel_at_period_end = False
    db.commit()
    db.refresh(subscription)

    return {"success": True, "status": subscription.status}



@router.patch("/payments/{payment_id}/status")
def admin_update_payment_status(
    payment_id: str,
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    status = payload.get("status")
    allowed = {"captured", "paid", "success", "succeeded", "failed", "refunded", "disputed"}

    if not status or status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid payment status")

    payment.status = status
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "success": True,
        "payment_id": str(payment.id),
        "status": payment.status,
    }



@router.get("/payments/{payment_id}/receipt")
def admin_payment_receipt(
    payment_id: str,
    db: Session = Depends(db_session),
) -> dict:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "payment": {
            "id": str(payment.id),
            "provider": payment.provider,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "provider_payment_id": payment.provider_payment_id,
            "provider_order_id": payment.provider_order_id,
            "created_at": payment.created_at,
        },
        "user": {
            "id": str(payment.user.id) if payment.user else None,
            "email": payment.user.email if payment.user else None,
        },
        "plan": {
            "name": payment.plan.name if payment.plan else None,
        },
        "company": {
            "name": "NeuralShieldDigital",
            "email": "neuralshielddigital@gmail.com",
        },
    }

@router.get("/refunds")
def admin_refunds(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    statuses = [
        "refunded",
        "disputed",
        "failed",
    ]

    query = (
        select(Payment)
        .options(
            selectinload(Payment.user),
            selectinload(Payment.plan),
        )
        .where(
            func.lower(Payment.status).in_(statuses)
        )
        .order_by(Payment.created_at.desc())
    )

    if search:
        term = f"%{search.strip()}%"

        query = (
            query
            .outerjoin(
                User,
                Payment.user_id == User.id,
            )
            .where(
                or_(
                    User.email.ilike(term),
                    Payment.provider_payment_id.ilike(term),
                    Payment.provider_order_id.ilike(term),
                    Payment.status.ilike(term),
                )
            )
        )

    total = (
        db.scalar(
            select(func.count())
            .select_from(query.subquery())
        )
        or 0
    )

    payments = db.scalars(
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [
            {
                "id": str(payment.id),
                "user_email": (
                    payment.user.email
                    if payment.user
                    else None
                ),
                "provider": payment.provider,
                "plan_name": (
                    payment.plan.name
                    if payment.plan
                    else None
                ),
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "provider_payment_id": (
                    payment.provider_payment_id
                ),
                "provider_order_id": (
                    payment.provider_order_id
                ),
                "created_at": payment.created_at,
            }
            for payment in payments
        ],
        "pagination": _pagination(
            page,
            page_size,
            int(total),
        ),
    }

@router.post("/refunds/{payment_id}/process")
def process_refund(
    payment_id: UUID,
    payload: dict | None = Body(default=None),
    current_admin: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        )
    ),
    db: Session = Depends(db_session),
) -> dict:
    payment = db.get(Payment, payment_id)

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    if str(payment.provider).lower() != "paddle":
        raise HTTPException(
            status_code=409,
            detail=(
                "Legacy-provider refunds are disabled. "
                "Use the original provider dashboard."
            ),
        )

    raise HTTPException(
        status_code=409,
        detail=(
            "Paddle refunds must currently be processed securely "
            "from the Paddle Transactions dashboard."
        ),
    )


@router.get("/api-keys")
def admin_api_keys(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = (
        select(APIKey)
        .options(selectinload(APIKey.user))
        .order_by(APIKey.created_at.desc())
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    keys = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "items": [
            {
                "id": str(k.id),
                "user_email": k.user.email if k.user else None,
                "key_name": k.name,
                "status": "revoked" if k.revoked else "active",
                "is_active": not k.revoked,
                "last_used_at": None,
                "created_at": k.created_at,
            }
            for k in keys
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.post("/api-keys/{api_key_id}/revoke")
def revoke_api_key(
    api_key_id: UUID,
    db: Session = Depends(db_session),
):
    key = db.get(APIKey, api_key_id)

    if not key:
        raise HTTPException(status_code=404, detail="API key not found.")

    key.revoked = True
    db.add(key)
    db.commit()

    return {"success": True}
@router.patch("/users/{user_id}/suspend")
def suspend_user(
    user_id: UUID,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
    return {"success": True}

@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: UUID,
    db: Session = Depends(db_session),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)

    db.commit()

    return {"success": True}
@router.patch("/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: UUID,
    db: Session = Depends(db_session),
):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = db.scalars(
        select(User).where(User.tenant_id == tenant.id)
    ).all()

    for user in users:
        user.is_active = False

    db.commit()
    return {"success": True}


@router.delete("/tenants/{tenant_id}")
def delete_tenant(
    tenant_id: UUID,
    db: Session = Depends(db_session),
):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    db.delete(tenant)
    db.commit()
    return {"success": True}
@router.get("/system-health")
def admin_system_health(
    db: Session = Depends(db_session),
) -> dict:
    try:
        db.execute(select(1))
        database_status = "ok"
    except Exception:
        database_status = "error"

    return {
        "backend": "ok",
        "database": database_status,
        "service": "NeuralShield FastAPI Backend",
        "environment": "production",
        "version": "0.1.0",
    }
@router.get("/incidents")
def admin_incidents(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    incident_keywords = [
        "failed",
        "suspicious",
        "threat",
        "blocked",
        "revoked",
        "deleted",
        "suspend",
        "error",
    ]

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
    )

    logs = db.scalars(query.limit(200)).all()

    incidents = []
    for log in logs:
        action = str(log.action or "").lower()
        metadata = log.metadata_ or {}

        if any(word in action for word in incident_keywords):
            severity = "HIGH" if any(word in action for word in ["threat", "blocked", "deleted", "revoked"]) else "MEDIUM"
            incidents.append({
                "id": str(log.id),
                "title": log.action,
                "severity": severity,
                "status": "OPEN",
                "source": log.user.email if log.user else "system",
                "created_at": log.created_at,
                "metadata": metadata,
            })

    total = len(incidents)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": incidents[start:end],
        "pagination": _pagination(page, page_size, total),
    }

@router.get("/support")
def admin_support_tickets(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    # Placeholder until real support ticket model is added.
    return {
        "items": [],
        "pagination": _pagination(page, page_size, 0),
    }
@router.get("/threat-intel")
def admin_threat_intel(
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)

    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(
            or_(
                AuditLog.action.ilike("%threat%"),
                AuditLog.action.ilike("%blocked%"),
                AuditLog.action.ilike("%malware%"),
                AuditLog.action.ilike("%breach%"),
            )
        )
        .order_by(AuditLog.created_at.desc())
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    logs = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()

    return {
        "items": [
            {
                "id": str(log.id),
                "indicator": log.action,
                "severity": "HIGH",
                "source": log.user.email if log.user else "system",
                "status": "ACTIVE",
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }
@router.get("/backups")
def admin_backups() -> dict:
    return {
        "items": [
            {
                "name": "daily-backup",
                "status": "completed",
                "storage": "local",
                "created_at": datetime.now(timezone.utc)
            }
        ]
    }
@router.get("/settings")
def admin_settings() -> dict:
    return {
        "app_name": "NeuralShieldDigital",
        "environment": "production",
        "payments": {
            "razorpay": True,
            "stripe": False
        },
        "security": {
            "ufw": True,
            "fail2ban": True,
            "jwt_auth": True
        },
        "database": "Neon PostgreSQL"
    }
import subprocess


@router.post("/backups/run")
def run_backup() -> dict:
    try:
        result = subprocess.run(
            ["/bin/bash", "/home/ubuntu/scripts/backup.sh"],
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

@router.patch("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: UUID,
    db: Session = Depends(db_session),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    if hasattr(user, "deleted_at"):
        user.deleted_at = None

    db.commit()
    return {"success": True}
@router.get("/risk-scores")
def admin_risk_scores():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "risk_score": 82,
                "risk_level": "HIGH",
                "last_activity": "Multiple failed logins",
                "created_at": "2026-06-18T10:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "risk_score": 45,
                "risk_level": "MEDIUM",
                "last_activity": "Password changed",
                "created_at": "2026-06-18T11:00:00Z"
            }
        ]
    }
@router.get("/compliance")
def admin_compliance():
    return {
        "items": [
            {
                "framework": "SOC2",
                "status": "Compliant",
                "score": 92,
                "last_check": "2026-06-18T12:00:00Z"
            },
            {
                "framework": "HIPAA",
                "status": "Pending",
                "score": 68,
                "last_check": "2026-06-18T12:10:00Z"
            },
            {
                "framework": "PCI-DSS",
                "status": "Compliant",
                "score": 88,
                "last_check": "2026-06-18T12:20:00Z"
            },
            {
                "framework": "ISO27001",
                "status": "In Review",
                "score": 74,
                "last_check": "2026-06-18T12:30:00Z"
            }
        ]
    }
@router.get("/activity-monitor")
def admin_activity_monitor():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "action": "login_failed",
                "resource": "auth_system",
                "severity": "HIGH",
                "created_at": "2026-06-18T13:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "action": "password_changed",
                "resource": "account_settings",
                "severity": "MEDIUM",
                "created_at": "2026-06-18T13:15:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "action": "role_updated",
                "resource": "tenant_permissions",
                "severity": "LOW",
                "created_at": "2026-06-18T13:30:00Z"
            }
        ]
    }
@router.get("/security-reports")
def admin_security_reports():
    return {
        "items": [
            {
                "title": "Executive Security Summary",
                "report_type": "executive",
                "status": "generated",
                "risk_level": "HIGH",
                "summary": "High employee risk detected due to failed login patterns and permission changes.",
                "created_at": "2026-06-18T14:00:00Z"
            },
            {
                "title": "Compliance Gap Report",
                "report_type": "compliance",
                "status": "generated",
                "risk_level": "MEDIUM",
                "summary": "HIPAA and ISO27001 checks require review.",
                "created_at": "2026-06-18T14:15:00Z"
            }
        ]
    }
@router.get("/policy-violations")
def admin_policy_violations():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "violation_type": "Unauthorized Access",
                "severity": "HIGH",
                "status": "Open",
                "details": "Attempted access to restricted finance records.",
                "created_at": "2026-06-18T15:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "violation_type": "External Data Sharing",
                "severity": "MEDIUM",
                "status": "Investigating",
                "details": "Sensitive file shared outside organization.",
                "created_at": "2026-06-18T15:20:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "violation_type": "Privilege Escalation",
                "severity": "CRITICAL",
                "status": "Resolved",
                "details": "Role escalation detected and reverted.",
                "created_at": "2026-06-18T15:40:00Z"
            }
        ]
    }
@router.get("/behavior-analytics")
def admin_behavior_analytics():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "login_frequency": "18/day",
                "device_changes": 3,
                "location_anomaly": "Yes",
                "failed_logins": 7,
                "session_risk_score": 89
            },
            {
                "user_email": "billingtest@example.com",
                "login_frequency": "6/day",
                "device_changes": 1,
                "location_anomaly": "No",
                "failed_logins": 1,
                "session_risk_score": 42
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "login_frequency": "10/day",
                "device_changes": 2,
                "location_anomaly": "Yes",
                "failed_logins": 3,
                "session_risk_score": 67
            }
        ]
    }
@router.get("/data-loss-prevention")
def admin_data_loss_prevention():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "event_type": "PII Export Attempt",
                "severity": "HIGH",
                "status": "Blocked",
                "details": "Customer SSN export detected."
            },
            {
                "user_email": "billingtest@example.com",
                "event_type": "External File Share",
                "severity": "MEDIUM",
                "status": "Investigating",
                "details": "Finance sheet shared to external domain."
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "event_type": "PHI Upload",
                "severity": "CRITICAL",
                "status": "Blocked",
                "details": "Healthcare records upload flagged."
            }
        ]
    }
@router.get("/device-monitoring")
def admin_device_monitoring():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "device_name": "MacBook Pro",
                "os": "macOS",
                "status": "Active",
                "last_seen": "2026-06-18T16:00:00Z",
                "risk_level": "LOW"
            },
            {
                "user_email": "billingtest@example.com",
                "device_name": "Windows Laptop",
                "os": "Windows 11",
                "status": "Suspicious",
                "last_seen": "2026-06-18T16:15:00Z",
                "risk_level": "HIGH"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "device_name": "Android Mobile",
                "os": "Android 15",
                "status": "Active",
                "last_seen": "2026-06-18T16:30:00Z",
                "risk_level": "MEDIUM"
            }
        ]
    }
@router.get("/access-control")
def admin_access_control():
    return {
        "items": [
            {
                "user_email": "vipul.chandera4@gmail.com",
                "role": "SUPER_ADMIN",
                "permission_change": "role_updated",
                "risk_level": "LOW",
                "status": "Approved",
                "created_at": "2026-06-18T17:00:00Z"
            },
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "role": "USER",
                "permission_change": "restricted_access_attempt",
                "risk_level": "HIGH",
                "status": "Blocked",
                "created_at": "2026-06-18T17:15:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "role": "ADMIN",
                "permission_change": "privilege_escalation_detected",
                "risk_level": "CRITICAL",
                "status": "Resolved",
                "created_at": "2026-06-18T17:30:00Z"
            }
        ]
    }
@router.get("/insider-threats")
def admin_insider_threats():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "threat_type": "Unusual Login Pattern",
                "severity": "HIGH",
                "status": "Investigating",
                "details": "Multiple off-hours logins detected.",
                "created_at": "2026-06-18T18:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "threat_type": "Mass File Download",
                "severity": "CRITICAL",
                "status": "Open",
                "details": "Downloaded 500+ sensitive files in one hour.",
                "created_at": "2026-06-18T18:15:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "threat_type": "Privilege Misuse",
                "severity": "MEDIUM",
                "status": "Resolved",
                "details": "Temporary admin access used outside policy.",
                "created_at": "2026-06-18T18:30:00Z"
            }
        ]
    }
@router.get("/endpoint-security")
def admin_endpoint_security():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "device_name": "MacBook Pro",
                "antivirus_status": "Active",
                "malware_detected": "No",
                "risk_level": "LOW",
                "last_scan": "2026-06-18T19:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "device_name": "Windows Laptop",
                "antivirus_status": "Disabled",
                "malware_detected": "Trojan.Win32",
                "risk_level": "CRITICAL",
                "last_scan": "2026-06-18T19:20:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "device_name": "Android Mobile",
                "antivirus_status": "Active",
                "malware_detected": "Suspicious APK",
                "risk_level": "HIGH",
                "last_scan": "2026-06-18T19:40:00Z"
            }
        ]
    }
@router.get("/email-security")
def admin_email_security():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "threat_type": "Phishing Attempt",
                "sender": "fake-paypal@secure-alert.com",
                "status": "Blocked",
                "risk_level": "HIGH",
                "created_at": "2026-06-18T20:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "threat_type": "Spoofed Domain",
                "sender": "admin@micros0ft-support.com",
                "status": "Quarantined",
                "risk_level": "CRITICAL",
                "created_at": "2026-06-18T20:15:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "threat_type": "Malicious Attachment",
                "sender": "invoice@unknownvendor.net",
                "status": "Blocked",
                "risk_level": "MEDIUM",
                "created_at": "2026-06-18T20:30:00Z"
            }
        ]
    }
@router.get("/cloud-access")
def admin_cloud_access():
    return {
        "items": [
            {
                "user_email": "testadmin@neuralshielddigital.com",
                "app_name": "Google Drive",
                "event_type": "External Share",
                "risk_level": "HIGH",
                "status": "Blocked",
                "created_at": "2026-06-18T21:00:00Z"
            },
            {
                "user_email": "billingtest@example.com",
                "app_name": "Dropbox",
                "event_type": "Sensitive Upload",
                "risk_level": "CRITICAL",
                "status": "Quarantined",
                "created_at": "2026-06-18T21:15:00Z"
            },
            {
                "user_email": "vipul.chandera4@gmail.com",
                "app_name": "Slack",
                "event_type": "Public Link Created",
                "risk_level": "MEDIUM",
                "status": "Investigating",
                "created_at": "2026-06-18T21:30:00Z"
            }
        ]
    }


@router.patch("/workflows/{workflow_id}/schedule")
def update_workflow_schedule(
    workflow_id: UUID,
    payload: dict,
    db: Session = Depends(db_session),
) -> dict:
    workflow = db.scalar(
    select(Workflow).where(Workflow.id == workflow_id)
)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow.schedule_enabled = bool(payload.get("schedule_enabled", False))
    workflow.schedule_cron = payload.get("schedule_cron")
    workflow.next_run_at = payload.get("next_run_at")

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    return {
        "id": str(workflow.id),
        "schedule_enabled": workflow.schedule_enabled,
        "schedule_cron": workflow.schedule_cron,
        "next_run_at": workflow.next_run_at,
    }

@router.post("/workflow-scheduler/run-due")
def admin_run_due_scheduled_workflows(
    db: Session = Depends(db_session),
) -> dict:
    return run_due_scheduled_workflows(db)

@router.post("/gmail-poller/run")
def admin_run_gmail_poller(
    db: Session = Depends(db_session),
):
    return run_gmail_new_email_poll(db)
