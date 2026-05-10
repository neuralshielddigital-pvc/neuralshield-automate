from __future__ import annotations

import secrets
import re
from math import ceil
from typing import Any
from uuid import UUID

import requests
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import WorkflowActionType, WorkflowRunStatus, WorkflowTriggerType
from app.models.security import AuditLog
from app.models.user import User
from app.models.workflow import Workflow, WorkflowAction, WorkflowRun, WorkflowTrigger
from app.schemas.campaign import PaginationMeta
from app.schemas.workflow import (
    PublicWorkflowWebhookResponse,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowRunListResponse,
    WorkflowUpdate,
)
from app.services.email_service import EmailService
from app.services.lead_service import LeadService


def _pagination(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_workflow(self, user: User, payload: WorkflowCreate) -> Workflow:
        workflow = Workflow(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            public_webhook_key=self._generate_public_webhook_key(),
            definition=self._definition(payload.trigger.model_dump(), [a.model_dump() for a in payload.actions]),
        )
        self.db.add(workflow)
        self.db.flush()
        self._replace_trigger_and_actions(workflow, payload.trigger.model_dump(), [a.model_dump() for a in payload.actions])
        self.db.commit()
        return self.get_workflow(user, workflow.id)

    def list_workflows(self, user: User, page: int, page_size: int) -> WorkflowListResponse:
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(Workflow).where(Workflow.tenant_id == user.tenant_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.options(selectinload(Workflow.triggers), selectinload(Workflow.actions))
            .order_by(Workflow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return WorkflowListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def get_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.db.scalar(
            select(Workflow)
            .options(selectinload(Workflow.triggers), selectinload(Workflow.actions))
            .where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id)
        )
        if workflow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
        return workflow

    def update_workflow(self, user: User, workflow_id: UUID, payload: WorkflowUpdate) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        changes = payload.model_dump(exclude_unset=True)
        for field in ["name", "description", "is_active"]:
            if field in changes:
                setattr(workflow, field, changes[field])
        if payload.trigger is not None or payload.actions is not None:
            trigger = payload.trigger.model_dump() if payload.trigger else workflow.triggers[0].__dict__
            actions = [a.model_dump() for a in payload.actions] if payload.actions else [
                {"type": action.type, "config": action.config} for action in workflow.actions
            ]
            workflow.definition = self._definition(trigger, actions)
            self._replace_trigger_and_actions(workflow, trigger, actions)
        self.db.commit()
        return self.get_workflow(user, workflow_id)

    def delete_workflow(self, user: User, workflow_id: UUID) -> None:
        workflow = self.get_workflow(user, workflow_id)
        self.db.delete(workflow)
        self.db.commit()

    def activate_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        workflow.is_active = True
        self.db.commit()
        return self.get_workflow(user, workflow_id)

    def deactivate_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        workflow.is_active = False
        self.db.commit()
        return self.get_workflow(user, workflow_id)

    def list_runs(self, user: User, workflow_id: UUID, page: int, page_size: int) -> WorkflowRunListResponse:
        workflow = self.get_workflow(user, workflow_id)
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(WorkflowRun).where(WorkflowRun.workflow_id == workflow.id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(WorkflowRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return WorkflowRunListResponse(items=list(items), pagination=_pagination(page, page_size, int(total)))

    def execute_public_webhook(self, public_webhook_key: str, payload: dict[str, Any]) -> PublicWorkflowWebhookResponse:
        workflow = self.db.scalar(
            select(Workflow)
            .options(selectinload(Workflow.triggers), selectinload(Workflow.actions))
            .where(Workflow.public_webhook_key == public_webhook_key, Workflow.is_active.is_(True))
        )
        if workflow is None or not any(t.type == WorkflowTriggerType.WEBHOOK_RECEIVED for t in workflow.triggers):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow webhook not found.")
        run = self._execute_workflow(workflow, WorkflowTriggerType.WEBHOOK_RECEIVED, payload)
        self.db.commit()
        return PublicWorkflowWebhookResponse(workflow_id=workflow.id, run_id=run.id, status=run.status)

    def execute_tenant_trigger(self, tenant_id: UUID, trigger_type: WorkflowTriggerType, payload: dict[str, Any]) -> None:
        workflows = self.db.scalars(
            select(Workflow)
            .options(selectinload(Workflow.triggers), selectinload(Workflow.actions))
            .join(WorkflowTrigger)
            .where(
                Workflow.tenant_id == tenant_id,
                Workflow.is_active.is_(True),
                WorkflowTrigger.type == trigger_type,
            )
        ).unique().all()
        for workflow in workflows:
            self._execute_workflow(workflow, trigger_type, payload)
        if workflows:
            self.db.commit()

    def _execute_workflow(self, workflow: Workflow, trigger_type: WorkflowTriggerType, payload: dict[str, Any]) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow.id,
            status=WorkflowRunStatus.RUNNING,
            trigger_payload={"trigger_type": trigger_type.value, "payload": payload},
            logs={"steps": []},
        )
        self.db.add(run)
        self.db.flush()
        logs: list[dict[str, Any]] = []
        try:
            for action in workflow.actions:
                result = self._execute_action(workflow, action, payload)
                logs.append({"action": action.type.value, "status": "success", "result": result})
            run.status = WorkflowRunStatus.COMPLETED
        except Exception as exc:
            logs.append({"status": "failed", "error": str(exc)})
            run.status = WorkflowRunStatus.FAILED
        run.logs = {"steps": logs}
        return run

    def _execute_action(self, workflow: Workflow, action: WorkflowAction, payload: dict[str, Any]) -> dict[str, Any]:
        if action.type == WorkflowActionType.SEND_WEBHOOK:
            url = self._render_value(action.config["url"], payload)
            response = requests.post(url, json={"workflow_id": str(workflow.id), "payload": payload}, timeout=10)
            return {"status_code": response.status_code, "ok": response.ok}
        if action.type == WorkflowActionType.SEND_EMAIL:
            to_email = self._render_value(action.config["to"], payload)
            subject = self._render_value(action.config["subject"], payload)
            body = self._render_value(action.config["body"], payload)
            return EmailService().send_email(to_email=to_email, subject=subject, body=body)
        if action.type == WorkflowActionType.CREATE_LEAD:
            email = self._render_value(action.config.get("email", "{{email}}"), payload).strip().lower()
            if not email:
                raise ValueError("CREATE_LEAD action resolved an empty email.")
            name = self._render_optional_value(action.config.get("name", "{{name}}"), payload)
            phone = self._render_optional_value(action.config.get("phone", "{{phone}}"), payload)
            source = self._render_optional_value(action.config.get("source", "{{source}}"), payload)
            tags = self._render_tags(action.config.get("tags", payload.get("tags", [])), payload)
            lead, created = LeadService(self.db).upsert_lead(
                user_id=workflow.user_id,
                tenant_id=workflow.tenant_id,
                name=name,
                email=email,
                phone=phone,
                source=source,
                tags=tags,
                metadata={"workflow_id": str(workflow.id), "payload": payload},
            )
            return {"lead_id": str(lead.id), "email": lead.email, "created": created}
        if action.type == WorkflowActionType.ADD_AUDIT_LOG:
            audit = AuditLog(
                user_id=workflow.user_id,
                action=action.config["action"],
                metadata_={"workflow_id": str(workflow.id), "payload": payload, "config": action.config},
            )
            self.db.add(audit)
            self.db.flush()
            return {"audit_log_id": str(audit.id)}
        raise ValueError(f"Unsupported action type: {action.type}")

    def _replace_trigger_and_actions(self, workflow: Workflow, trigger: dict, actions: list[dict]) -> None:
        workflow.triggers.clear()
        workflow.actions.clear()
        self.db.flush()
        workflow.triggers.append(WorkflowTrigger(type=trigger["type"], config=trigger.get("config", {})))
        for action in actions:
            workflow.actions.append(WorkflowAction(type=action["type"], config=action.get("config", {})))

    def _definition(self, trigger: dict, actions: list[dict]) -> dict:
        return {"trigger": trigger, "actions": actions}

    def _render_tags(self, value: Any, payload: dict[str, Any]) -> list[str]:
        if isinstance(value, list):
            return [self._render_value(item, payload).strip() for item in value if self._render_value(item, payload).strip()]
        if isinstance(value, str):
            rendered = self._render_value(value, payload)
            return [tag.strip() for tag in rendered.split(",") if tag.strip()]
        return []

    def _render_optional_value(self, value: Any, payload: dict[str, Any]) -> str | None:
        if value is None:
            return None
        rendered = self._render_value(value, payload).strip()
        return rendered or None

    def _render_value(self, value: Any, payload: dict[str, Any]) -> str:
        if not isinstance(value, str):
            return "" if value is None else str(value)

        def replace_match(match: re.Match[str]) -> str:
            key_path = match.group(1).strip()
            resolved = self._resolve_payload_value(key_path, payload)
            return "" if resolved is None else str(resolved)

        rendered = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace_match, value)
        try:
            return rendered.format(**payload)
        except (KeyError, IndexError, ValueError):
            return rendered

    def _resolve_payload_value(self, key_path: str, payload: dict[str, Any]) -> Any:
        current: Any = payload
        parts = key_path.split(".")
        if parts and parts[0] == "payload":
            parts = parts[1:]
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def _generate_public_webhook_key(self) -> str:
        for _ in range(10):
            key = secrets.token_urlsafe(32)
            exists = self.db.scalar(select(Workflow.id).where(Workflow.public_webhook_key == key))
            if exists is None:
                return key
        return secrets.token_urlsafe(48)

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int]:
        return max(page, 1), min(max(page_size, 1), 100)
