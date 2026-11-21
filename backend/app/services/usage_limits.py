from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from app.core.config import settings
from sqlalchemy.orm import Session

from app.models.billing import Plan, Subscription
from app.models.whop_saas_subscription import WhopSaasSubscriptionBinding
from app.models.enums import SubscriptionStatus
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun


UNLIMITED = -1
# Expiring provider snapshots prevent a missed cancellation webhook from
# granting paid limits indefinitely. A trusted reconciliation worker MUST
# refresh provider facts regularly before this feature is activated.
WHOP_SAAS_SNAPSHOT_TTL = timedelta(hours=24)


def whop_snapshot_is_fresh(observed_at: datetime | None, *, now: datetime | None = None) -> bool:
    if observed_at is None or not isinstance(observed_at, datetime):
        return False
    # Some drivers (including SQLite tests) return naive UTC timestamps.
    # The backend writes timezone-aware UTC; naive values are interpreted UTC.
    observed = observed_at.replace(tzinfo=timezone.utc) if observed_at.tzinfo is None else observed_at.astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Current time must be timezone aware")
    elapsed = current.astimezone(timezone.utc) - observed
    return timedelta(0) <= elapsed <= WHOP_SAAS_SNAPSHOT_TTL



PLAN_LIMITS: dict[str, dict[str, int]] = {
    "starter": {
        "workflows": 5,
        "monthly_runs": 500,
        "webhooks": 1,
    },
    "pro": {
        "workflows": 25,
        "monthly_runs": 5_000,
        "webhooks": UNLIMITED,
    },
    # Database still stores "Enterprise";
    # customer-facing name is "Business".
    "enterprise": {
        "workflows": UNLIMITED,
        "monthly_runs": UNLIMITED,
        "webhooks": UNLIMITED,
    },
}

FREE_LIMITS: dict[str, int] = {
    "workflows": 2,
    "monthly_runs": 100,
    "webhooks": 1,
}


def month_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def get_verified_whop_tier(db: Session, user: User) -> str | None:
    """Opt-in Whop SaaS entitlement lookup, isolated from Paddle.

    Returns None when the feature is disabled or a Whop subscription has
    not been bound to this user and tenant. Revoked/past-due Whop rows never
    provide paid limits. Authentication and authoritative provider lifecycle
    persistence must be configured before this flag may be enabled.
    """
    if not getattr(settings, "AGENCY_SAAS_WHOP_LIMITS_ENABLED", False):
        return None
    if getattr(user, "tenant_id", None) is None:
        return None
    rows = (
        db.query(WhopSaasSubscriptionBinding)
        .filter(
            WhopSaasSubscriptionBinding.user_id == user.id,
            WhopSaasSubscriptionBinding.tenant_id == user.tenant_id,
        )
        .all()
    )
    active = [
        row for row in rows
        if row.access_enabled is True
        and row.access_state == "active"
        and whop_snapshot_is_fresh(row.provider_observed_at)
        and row.tier in {"starter", "pro", "business"}
    ]
    # Multiple active Whop subscriptions for one user require a manual
    # resolution, not implicit highest-tier privilege escalation.
    if len(active) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Multiple active SaaS subscriptions require support review.",
        )
    if not active:
        return None
    return "enterprise" if active[0].tier == "business" else active[0].tier


def get_active_plan_name(db: Session, user: User) -> str:
    whop_tier = get_verified_whop_tier(db, user)
    if whop_tier is not None:
        return whop_tier

    query = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == SubscriptionStatus.ACTIVE,
    )

    if getattr(user, "tenant_id", None):
        query = query.filter(
            Subscription.tenant_id == user.tenant_id,
        )

    subscription = query.order_by(
        Subscription.created_at.desc(),
    ).first()

    if not subscription:
        return "free"

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id,
    ).first()

    if not plan or not plan.name:
        return "free"

    normalized_name = str(plan.name).strip().lower()

    return normalized_name if normalized_name in PLAN_LIMITS else "free"


def get_plan_limits(db: Session, user: User) -> dict[str, int]:
    plan_name = get_active_plan_name(db, user)

    limits = PLAN_LIMITS.get(plan_name, FREE_LIMITS)

    # Return a copy so callers cannot mutate global limit configuration.
    return dict(limits)


def tenant_workflow_filter(query: Any, user: User):
    if getattr(user, "tenant_id", None):
        return query.filter(
            Workflow.tenant_id == user.tenant_id,
        )

    return query.filter(
        Workflow.user_id == user.id,
    )


def get_workflow_count(db: Session, user: User) -> int:
    query = db.query(Workflow)
    query = tenant_workflow_filter(query, user)

    return query.count()


def get_monthly_run_count(db: Session, user: User) -> int:
    query = (
        db.query(WorkflowRun)
        .join(
            Workflow,
            WorkflowRun.workflow_id == Workflow.id,
        )
        .filter(
            WorkflowRun.created_at >= month_start_utc(),
        )
    )

    query = tenant_workflow_filter(query, user)

    return query.count()


def enforce_workflow_create_limit(
    db: Session,
    user: User,
) -> None:
    limits = get_plan_limits(db, user)
    limit = limits["workflows"]

    if limit == UNLIMITED:
        return

    count = get_workflow_count(db, user)

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Workflow limit reached for your plan. "
                f"Limit: {limit}. Upgrade to create more workflows."
            ),
        )


def enforce_monthly_run_limit(
    db: Session,
    user: User,
) -> None:
    limits = get_plan_limits(db, user)
    limit = limits["monthly_runs"]

    if limit == UNLIMITED:
        return

    count = get_monthly_run_count(db, user)

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Monthly workflow run limit reached for your plan. "
                f"Limit: {limit}. Upgrade to continue running workflows."
            ),
        )
