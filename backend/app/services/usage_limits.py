from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.billing import Plan, Subscription
from app.models.enums import SubscriptionStatus
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun


UNLIMITED = -1

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


def get_active_plan_name(db: Session, user: User) -> str:
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
