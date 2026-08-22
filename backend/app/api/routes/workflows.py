from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.enums import WorkflowRunStatus, WorkflowTriggerType
from app.models.user import User
from app.models.workflow import Workflow, WorkflowRun
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowRead,
    WorkflowRunListResponse,
    WorkflowRunRead,
    WorkflowUpdate,
)
from app.services.usage_limits import (
    UNLIMITED,
    get_active_plan_name,
    get_plan_limits,
    month_start_utc,
)
from app.services.workflow_service import WorkflowService
from app.services.usage_limits import (
    enforce_monthly_run_limit,
    enforce_workflow_create_limit,
)


router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    enforce_workflow_create_limit(db, current_user)
    return WorkflowService(db).create_workflow(current_user, payload)


@router.get("", response_model=WorkflowListResponse)
def list_workflows(
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowListResponse:
    return WorkflowService(db).list_workflows(current_user, page, page_size)


@router.get("/usage-summary")
def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    month_start = month_start_utc()

    workflow_query = db.query(Workflow)

    if current_user.tenant_id:
        workflow_query = workflow_query.filter(
            Workflow.tenant_id == current_user.tenant_id
        )
    else:
        workflow_query = workflow_query.filter(
            Workflow.user_id == current_user.id
        )

    total_workflows = workflow_query.count()

    active_workflows = workflow_query.filter(
        Workflow.is_active.is_(True)
    ).count()

    run_query = (
        db.query(WorkflowRun)
        .join(
            Workflow,
            WorkflowRun.workflow_id == Workflow.id,
        )
        .filter(
            WorkflowRun.created_at >= month_start,
        )
    )

    if current_user.tenant_id:
        run_query = run_query.filter(
            Workflow.tenant_id == current_user.tenant_id
        )
    else:
        run_query = run_query.filter(
            Workflow.user_id == current_user.id
        )

    monthly_runs = run_query.count()

    completed_runs = run_query.filter(
        WorkflowRun.status == WorkflowRunStatus.COMPLETED
    ).count()

    failed_runs = run_query.filter(
        WorkflowRun.status == WorkflowRunStatus.FAILED
    ).count()

    running_runs = run_query.filter(
        WorkflowRun.status == WorkflowRunStatus.RUNNING
    ).count()

    queued_runs = run_query.filter(
        WorkflowRun.status == WorkflowRunStatus.QUEUED
    ).count()

    finished_runs = completed_runs + failed_runs

    success_rate = (
        round((completed_runs / finished_runs) * 100, 1)
        if finished_runs > 0
        else 0.0
    )

    plan_name = get_active_plan_name(db, current_user)
    limits = get_plan_limits(db, current_user)

    workflow_limit = limits["workflows"]
    monthly_run_limit = limits["monthly_runs"]

    remaining_runs = (
        None
        if monthly_run_limit == UNLIMITED
        else max(monthly_run_limit - monthly_runs, 0)
    )

    remaining_workflows = (
        None
        if workflow_limit == UNLIMITED
        else max(workflow_limit - total_workflows, 0)
    )

    recent_runs_query = (
        db.query(WorkflowRun, Workflow)
        .join(
            Workflow,
            WorkflowRun.workflow_id == Workflow.id,
        )
    )

    if current_user.tenant_id:
        recent_runs_query = recent_runs_query.filter(
            Workflow.tenant_id == current_user.tenant_id
        )
    else:
        recent_runs_query = recent_runs_query.filter(
            Workflow.user_id == current_user.id
        )

    recent_runs = (
        recent_runs_query
        .order_by(WorkflowRun.created_at.desc())
        .limit(5)
        .all()
    )

    top_workflows_query = (
        db.query(
            Workflow.id,
            Workflow.name,
            Workflow.is_active,
            func.count(WorkflowRun.id).label("run_count"),
        )
        .outerjoin(
            WorkflowRun,
            and_(
                WorkflowRun.workflow_id == Workflow.id,
                WorkflowRun.created_at >= month_start,
            ),
        )
    )

    if current_user.tenant_id:
        top_workflows_query = top_workflows_query.filter(
            Workflow.tenant_id == current_user.tenant_id
        )
    else:
        top_workflows_query = top_workflows_query.filter(
            Workflow.user_id == current_user.id
        )

    top_workflows = (
        top_workflows_query
        .group_by(
            Workflow.id,
            Workflow.name,
            Workflow.is_active,
        )
        .order_by(
            func.count(WorkflowRun.id).desc(),
            Workflow.name.asc(),
        )
        .limit(5)
        .all()
    )

    display_plan_name = (
        "Business"
        if plan_name == "enterprise"
        else plan_name.capitalize()
    )

    return {
        "period": {
            "start": month_start,
            "label": month_start.strftime("%B %Y"),
        },
        "plan": {
            "name": display_plan_name,
            "internal_name": plan_name,
            "workflow_limit": workflow_limit,
            "monthly_run_limit": monthly_run_limit,
            "remaining_workflows": remaining_workflows,
            "remaining_runs": remaining_runs,
        },
        "workflows": {
            "total": total_workflows,
            "active": active_workflows,
            "inactive": max(total_workflows - active_workflows, 0),
        },
        "runs": {
            "total": monthly_runs,
            "completed": completed_runs,
            "failed": failed_runs,
            "running": running_runs,
            "queued": queued_runs,
            "success_rate": success_rate,
        },
        "recent_runs": [
            {
                "id": run.id,
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "status": run.status.value,
                "created_at": run.created_at,
                "last_error": run.last_error,
            }
            for run, workflow in recent_runs
        ],
        "top_workflows": [
            {
                "id": workflow_id,
                "name": workflow_name,
                "is_active": is_active,
                "run_count": int(run_count),
            }
            for workflow_id, workflow_name, is_active, run_count in top_workflows
        ],
    }


@router.post("/test-gmail-trigger")
def test_gmail_trigger(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> dict:
    payload = {
        "id": "test-gmail-message",
        "thread_id": "test-gmail-thread",
        "subject": "Test Gmail Trigger",
        "from": "sender@example.com",
        "to": current_user.email,
        "snippet": "This is a test Gmail email payload.",
        "body": "This is a test Gmail email body.",
        "source": "gmail",
    }

    WorkflowService(db).execute_tenant_trigger(
        current_user.tenant_id,
        WorkflowTriggerType.GMAIL_NEW_EMAIL,
        payload,
    )

    return {
        "success": True,
        "trigger_type": "GMAIL_NEW_EMAIL",
        "message": "Gmail trigger test executed.",
        "payload": payload,
    }


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).get_workflow(current_user, workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).update_workflow(
        current_user,
        workflow_id,
        payload,
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Response:
    WorkflowService(db).delete_workflow(
        current_user,
        workflow_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workflow_id}/activate", response_model=WorkflowRead)
def activate_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).activate_workflow(
        current_user,
        workflow_id,
    )


@router.post("/{workflow_id}/deactivate", response_model=WorkflowRead)
def deactivate_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).deactivate_workflow(
        current_user,
        workflow_id,
    )


@router.post("/{workflow_id}/run", response_model=WorkflowRunRead)
def manual_run_workflow(
    workflow_id: UUID,
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRunRead:
    enforce_monthly_run_limit(db, current_user)

    return WorkflowService(db).manual_run_workflow(
        current_user,
        workflow_id,
        payload,
    )


@router.get(
    "/{workflow_id}/runs",
    response_model=WorkflowRunListResponse,
)
def list_workflow_runs(
    workflow_id: UUID,
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRunListResponse:
    return WorkflowService(db).list_runs(
        current_user,
        workflow_id,
        page,
        page_size,
    )
