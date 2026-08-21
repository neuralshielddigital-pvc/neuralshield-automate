from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.workflow_template import WorkflowTemplate
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate
from app.services.workflow_service import WorkflowService
from app.services.usage_limits import enforce_workflow_create_limit


class WorkflowTemplatePayload(BaseModel):
    name: str
    description: str | None = None
    category: str
    is_active: bool = True
    definition: dict
    is_featured: bool = False
    is_new: bool = True
    install_count: int = 0
    difficulty: str = "Beginner"
    estimated_setup_minutes: int = 5
    tags: list[str] = []


class WorkflowTemplateRead(WorkflowTemplatePayload):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class WorkflowTemplateList(BaseModel):
    items: list[WorkflowTemplateRead]


router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


@router.get("", response_model=WorkflowTemplateList)
def list_workflow_templates(
    db: Session = Depends(db_session),
) -> WorkflowTemplateList:
    items = db.scalars(
        select(WorkflowTemplate)
        .where(WorkflowTemplate.is_active.is_(True))
        .order_by(WorkflowTemplate.category.asc(), WorkflowTemplate.name.asc())
    ).all()
    return WorkflowTemplateList(items=list(items))


@router.post("", response_model=WorkflowTemplateRead, status_code=status.HTTP_201_CREATED)
def create_workflow_template(
    payload: WorkflowTemplatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowTemplate:
    template = WorkflowTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=WorkflowTemplateRead)
def update_workflow_template(
    template_id: UUID,
    payload: WorkflowTemplatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> WorkflowTemplate:
    template = db.get(WorkflowTemplate, template_id)
    if template is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Workflow template not found.")

    for key, value in payload.model_dump().items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return template



@router.post("/{template_id}/clone")
def clone_workflow_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):

    template = db.get(WorkflowTemplate, template_id)
    if template is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Workflow template not found.")

    enforce_workflow_create_limit(db, current_user)
    workflow_name = f"{template.name} Copy"

    existing_workflow = db.scalar(
        select(Workflow).where(
            Workflow.tenant_id == current_user.tenant_id,
            Workflow.name == workflow_name,
        )
    )

    if existing_workflow is not None:
        return {
            "id": str(existing_workflow.id),
            "name": existing_workflow.name,
            "already_installed": True,
        }

    payload = WorkflowCreate(
        name=workflow_name,
        description=template.description,
        is_active=False,
        trigger=template.definition["trigger"],
        actions=template.definition["actions"],
    )

    workflow = WorkflowService(db).create_workflow(current_user, payload)

    template.install_count = (template.install_count or 0) + 1
    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "already_installed": False,
    }


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Response:
    template = db.get(WorkflowTemplate, template_id)
    if template is not None:
        db.delete(template)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
