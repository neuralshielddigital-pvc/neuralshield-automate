from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.models.user import User
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


def _next_month_start_utc(now: datetime) -> datetime:
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)

    return datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)


def run_due_scheduled_workflows(db: Session) -> dict:
    now = datetime.now(timezone.utc)

    workflow_ids = db.scalars(
        select(Workflow.id)
        .where(
            Workflow.is_active.is_(True),
            Workflow.schedule_enabled.is_(True),
            Workflow.next_run_at.is_not(None),
            Workflow.next_run_at <= now,
        )
        .order_by(Workflow.next_run_at.asc())
    ).all()

    # End the read transaction before claiming individual workflow rows.
    db.rollback()

    executed = 0
    deferred = 0
    failed = 0

    for workflow_id in workflow_ids:
        try:
            workflow = db.scalar(
                select(Workflow)
                .where(
                    Workflow.id == workflow_id,
                    Workflow.is_active.is_(True),
                    Workflow.schedule_enabled.is_(True),
                    Workflow.next_run_at.is_not(None),
                    Workflow.next_run_at <= now,
                )
                .with_for_update(skip_locked=True)
            )

            if workflow is None:
                db.rollback()
                continue

            user = db.get(User, workflow.user_id)
            if user is None:
                db.rollback()
                failed += 1
                logger.error(
                    "Scheduled workflow owner not found: workflow_id=%s",
                    workflow_id,
                )
                continue

            next_run_at = WorkflowService.next_run_from_cron(
                workflow.schedule_cron,
                now,
            )

            try:
                WorkflowService(db).manual_run_workflow(
                    user=user,
                    workflow_id=workflow.id,
                    payload={
                        "scheduled": True,
                        "triggered_at": now.isoformat(),
                    },
                    commit=False,
                )
            except HTTPException as exc:
                is_monthly_limit = (
                    exc.status_code == status.HTTP_402_PAYMENT_REQUIRED
                    and str(exc.detail).startswith(
                        "Monthly workflow run limit reached"
                    )
                )

                if not is_monthly_limit:
                    raise

                db.rollback()

                deferred_workflow = db.get(Workflow, workflow_id)
                if deferred_workflow is not None:
                    deferred_workflow.next_run_at = _next_month_start_utc(now)
                    db.add(deferred_workflow)
                    db.commit()

                deferred += 1
                logger.warning(
                    "Scheduled workflow deferred until monthly quota reset: "
                    "workflow_id=%s next_run_at=%s",
                    workflow_id,
                    _next_month_start_utc(now).isoformat(),
                )
                continue

            workflow.last_scheduled_run_at = now
            workflow.next_run_at = next_run_at

            db.add(workflow)
            db.commit()
            executed += 1

        except Exception:
            db.rollback()
            failed += 1
            logger.exception(
                "Scheduled workflow failed: %s",
                workflow_id,
            )

    return {
        "checked": len(workflow_ids),
        "executed": executed,
        "deferred": deferred,
        "failed": failed,
    }
