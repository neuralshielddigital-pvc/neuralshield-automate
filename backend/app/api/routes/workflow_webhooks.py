from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.workflow import PublicWorkflowWebhookResponse
from app.services.workflow_service import WorkflowService


router = APIRouter(prefix="/webhooks/workflow", tags=["workflow-webhooks"])


@router.post("/{public_webhook_key}", response_model=PublicWorkflowWebhookResponse)
def receive_workflow_webhook(
    public_webhook_key: str,
    payload: dict[str, Any],
    db: Session = Depends(db_session),
) -> PublicWorkflowWebhookResponse:
    return WorkflowService(db).execute_public_webhook(public_webhook_key.strip(), payload)
