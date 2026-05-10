from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.workflow import WorkflowCreate, WorkflowListResponse, WorkflowRead, WorkflowRunListResponse, WorkflowUpdate
from app.services.workflow_service import WorkflowService


router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).create_workflow(current_user, payload)


@router.get("", response_model=WorkflowListResponse)
def list_workflows(
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowListResponse:
    return WorkflowService(db).list_workflows(current_user, page, page_size)


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
    return WorkflowService(db).update_workflow(current_user, workflow_id, payload)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Response:
    WorkflowService(db).delete_workflow(current_user, workflow_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workflow_id}/activate", response_model=WorkflowRead)
def activate_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).activate_workflow(current_user, workflow_id)


@router.post("/{workflow_id}/deactivate", response_model=WorkflowRead)
def deactivate_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRead:
    return WorkflowService(db).deactivate_workflow(current_user, workflow_id)


@router.get("/{workflow_id}/runs", response_model=WorkflowRunListResponse)
def list_workflow_runs(
    workflow_id: UUID,
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowRunListResponse:
    return WorkflowService(db).list_runs(current_user, workflow_id, page, page_size)
