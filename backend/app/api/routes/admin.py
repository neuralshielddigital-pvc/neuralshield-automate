from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_roles
from app.models.affiliate import Affiliate, Commission
from app.models.billing import Subscription
from app.models.enums import CommissionStatus, SubscriptionStatus, UserRole
from app.models.marketing import CampaignLead
from app.models.security import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun
from app.schemas.affiliate import CommissionActionResponse
from app.services.affiliate_service import AffiliateService


router = APIRouter(prefix="/admin", tags=["admin"])


def _pagination(page: int, page_size: int, total: int) -> dict:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


def _normalize_pagination(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def _tenant_name(db: Session, tenant_id) -> str | None:
    tenant = db.get(Tenant, tenant_id)
    return tenant.name if tenant else None


AdminAccess = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))


@router.get("/stats")
def admin_stats(
    _: User = AdminAccess,
    db: Session = Depends(db_session),
) -> dict:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_subscriptions = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.ACTIVE)
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


@router.get("/users")
def admin_users(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    _: User = AdminAccess,
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


@router.get("/subscriptions")
def admin_subscriptions(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    _: User = AdminAccess,
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
    _: User = AdminAccess,
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
    _: User = AdminAccess,
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


@router.get("/workflow-runs")
def admin_workflow_runs(
    page: int = 1,
    page_size: int = 25,
    _: User = AdminAccess,
    db: Session = Depends(db_session),
) -> dict:
    page, page_size = _normalize_pagination(page, page_size)
    query = select(WorkflowRun).options(selectinload(WorkflowRun.workflow)).order_by(WorkflowRun.created_at.desc())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    runs = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
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
                "created_at": run.created_at,
            }
            for run in runs
        ],
        "pagination": _pagination(page, page_size, int(total)),
    }


@router.get("/affiliates")
def admin_affiliates(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    _: User = AdminAccess,
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
    _: User = AdminAccess,
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
    _: User = AdminAccess,
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


@router.post("/commissions/{commission_id}/approve", response_model=CommissionActionResponse)
def approve_commission(
    commission_id: UUID,
    _: User = AdminAccess,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.APPROVED)


@router.post("/commissions/{commission_id}/reject", response_model=CommissionActionResponse)
def reject_commission(
    commission_id: UUID,
    _: User = AdminAccess,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.REJECTED)


@router.post("/commissions/{commission_id}/mark-paid", response_model=CommissionActionResponse)
def mark_commission_paid(
    commission_id: UUID,
    _: User = AdminAccess,
    db: Session = Depends(db_session),
) -> CommissionActionResponse:
    return AffiliateService(db).update_commission_status(commission_id, CommissionStatus.PAID)
