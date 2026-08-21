from __future__ import annotations

import secrets
import re
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any
from uuid import UUID
from app.core.config import settings

from google.oauth2 import service_account
from googleapiclient.discovery import build

import requests
from app.core.encryption import decrypt_secret
from app.core.outbound_http import (
    safe_outbound_request,
    sanitized_url_for_result,
)
from app.models.integration import IntegrationCredential
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
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
from app.services.usage_limits import enforce_monthly_run_limit


MAX_SYNC_WAIT_SECONDS = 30


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

    @staticmethod
    def next_run_from_cron(
        cron_expr: str | None,
        now: datetime | None = None,
    ) -> datetime | None:
        if not cron_expr:
            return None

        current = now or datetime.now(timezone.utc)
        normalized = cron_expr.strip()

        if normalized == "0 */6 * * *":
            return current + timedelta(hours=6)

        if normalized == "0 */12 * * *":
            return current + timedelta(hours=12)

        if normalized == "0 0 * * *":
            return current + timedelta(days=1)

        raise ValueError("Unsupported workflow schedule.")

    @staticmethod
    def _is_scheduled_trigger(workflow: Workflow) -> bool:
        return bool(
            workflow.triggers
            and workflow.triggers[0].type == WorkflowTriggerType.SCHEDULED
        )

    def _validate_schedule_configuration(
        self,
        workflow: Workflow,
    ) -> None:
        if not self._is_scheduled_trigger(workflow):
            return

        if not workflow.schedule_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled workflow must have scheduling enabled.",
            )

        if not workflow.schedule_cron:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled workflow requires a schedule.",
            )

        try:
            self.next_run_from_cron(workflow.schedule_cron)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported workflow schedule.",
            ) from error

    def create_workflow(self, user: User, payload: WorkflowCreate) -> Workflow:
        schedule_enabled = (
            payload.trigger.type == WorkflowTriggerType.SCHEDULED
            and payload.schedule_enabled
        )
        schedule_cron = (
            payload.schedule_cron
            if schedule_enabled
            else None
        )

        workflow = Workflow(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name=payload.name,
            description=payload.description,
            is_active=payload.is_active,
            schedule_enabled=schedule_enabled,
            schedule_cron=schedule_cron,
            next_run_at=(
                self.next_run_from_cron(schedule_cron)
                if schedule_enabled and payload.is_active
                else None
            ),
            public_webhook_key=self._generate_public_webhook_key(),
            definition=self._definition(
                payload.trigger.model_dump(),
                [action.model_dump() for action in payload.actions],
            ),
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
        meta = _pagination(page, page_size, int(total))

        return WorkflowListResponse(
        items=list(items),
        pagination={
        "page": meta.page,
        "page_size": meta.page_size,
        "total": meta.total,
        "total_pages": meta.total_pages,
    }
)

    def get_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.db.scalar(
            select(Workflow)
            .options(selectinload(Workflow.triggers), selectinload(Workflow.actions))
            .where(Workflow.id == workflow_id, Workflow.tenant_id == user.tenant_id)
        )
        if workflow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
        return workflow

    def update_workflow(
        self,
        user: User,
        workflow_id: UUID,
        payload: WorkflowUpdate,
    ) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        changes = payload.model_dump(exclude_unset=True)

        for field in ["name", "description", "is_active"]:
            if field in changes:
                setattr(workflow, field, changes[field])

        if payload.trigger is not None or payload.actions is not None:
            trigger = (
                payload.trigger.model_dump()
                if payload.trigger
                else {
                    "type": workflow.triggers[0].type,
                    "config": workflow.triggers[0].config,
                }
            )
            actions = (
                [action.model_dump() for action in payload.actions]
                if payload.actions
                else [
                    {
                        "type": action.type,
                        "config": action.config,
                    }
                    for action in workflow.actions
                ]
            )

            workflow.definition = self._definition(trigger, actions)
            self._replace_trigger_and_actions(workflow, trigger, actions)

        effective_trigger_type = (
            payload.trigger.type
            if payload.trigger is not None
            else (
                workflow.triggers[0].type
                if workflow.triggers
                else None
            )
        )

        if effective_trigger_type != WorkflowTriggerType.SCHEDULED:
            workflow.schedule_enabled = False
            workflow.schedule_cron = None
            workflow.next_run_at = None
        else:
            if "schedule_enabled" in changes:
                workflow.schedule_enabled = bool(
                    changes["schedule_enabled"]
                )

            if "schedule_cron" in changes:
                workflow.schedule_cron = changes["schedule_cron"]

            if not workflow.schedule_enabled:
                workflow.next_run_at = None
            elif workflow.is_active:
                workflow.next_run_at = self.next_run_from_cron(
                    workflow.schedule_cron
                )
            else:
                workflow.next_run_at = None

        self.db.commit()
        return self.get_workflow(user, workflow_id)

    def delete_workflow(self, user: User, workflow_id: UUID) -> None:
        workflow = self.get_workflow(user, workflow_id)

        self.db.execute(
            delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow.id)
        )
        self.db.execute(
            delete(WorkflowAction).where(WorkflowAction.workflow_id == workflow.id)
        )
        self.db.execute(
            delete(WorkflowTrigger).where(WorkflowTrigger.workflow_id == workflow.id)
        )
        self.db.execute(
            delete(Workflow).where(Workflow.id == workflow.id)
        )

        self.db.commit()

    @staticmethod
    def _has_configured_value(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _collect_action_configuration_issues(
        self,
        action_type: Any,
        config: dict[str, Any] | None,
        step_label: str,
    ) -> list[str]:
        config = config or {}
        type_value = getattr(action_type, "value", action_type)
        type_value = str(type_value)

        issues: list[str] = []

        if type_value == WorkflowActionType.SLACK_SEND_MESSAGE.value:
            if not (
                self._has_configured_value(config.get("channel"))
                or self._has_configured_value(config.get("channel_id"))
            ):
                issues.append(f"{step_label}: Slack channel or channel ID is required.")

            if not (
                self._has_configured_value(config.get("message"))
                or self._has_configured_value(config.get("text"))
            ):
                issues.append(f"{step_label}: Slack message is required.")

        elif type_value == WorkflowActionType.SEND_EMAIL.value:
            if not self._has_configured_value(config.get("to")):
                issues.append(f"{step_label}: Email recipient is required.")

            if not self._has_configured_value(config.get("subject")):
                issues.append(f"{step_label}: Email subject is required.")

            if not self._has_configured_value(config.get("body")):
                issues.append(f"{step_label}: Email body is required.")

        elif type_value == WorkflowActionType.SEND_WEBHOOK.value:
            if not self._has_configured_value(config.get("url")):
                issues.append(f"{step_label}: Webhook URL is required.")

        elif type_value == WorkflowActionType.HTTP_REQUEST.value:
            if not self._has_configured_value(config.get("url")):
                issues.append(f"{step_label}: HTTP request URL is required.")

        elif type_value == WorkflowActionType.GOOGLE_SHEETS_APPEND.value:
            if not self._has_configured_value(config.get("spreadsheet_id")):
                issues.append(f"{step_label}: Google Spreadsheet ID is required.")

            if not self._has_configured_value(config.get("sheet_name")):
                issues.append(f"{step_label}: Google Sheet name is required.")

        elif type_value == WorkflowActionType.OPENAI_TEXT_GENERATE.value:
            if not self._has_configured_value(config.get("prompt")):
                issues.append(f"{step_label}: OpenAI prompt is required.")

            if not self._has_configured_value(config.get("model")):
                issues.append(f"{step_label}: OpenAI model is required.")

        if type_value == WorkflowActionType.CONDITION.value:
            for branch_key, branch_name in (
                ("on_true", "true branch"),
                ("on_false", "false branch"),
            ):
                branch_actions = config.get(branch_key)

                if not isinstance(branch_actions, list):
                    continue

                for branch_index, branch_action in enumerate(branch_actions, start=1):
                    if not isinstance(branch_action, dict):
                        issues.append(
                            f"{step_label} {branch_name} step {branch_index}: "
                            "Invalid action configuration."
                        )
                        continue

                    issues.extend(
                        self._collect_action_configuration_issues(
                            branch_action.get("type"),
                            branch_action.get("config")
                            if isinstance(branch_action.get("config"), dict)
                            else {},
                            (
                                f"{step_label} {branch_name} "
                                f"step {branch_index}"
                            ),
                        )
                    )

        return issues

    def _validate_workflow_configuration(self, workflow: Workflow) -> None:
        self._validate_schedule_configuration(workflow)

        issues: list[str] = []

        if not workflow.triggers:
            issues.append("Workflow trigger is required.")

        if not workflow.actions:
            issues.append("At least one workflow action is required.")

        for index, action in enumerate(workflow.actions, start=1):
            issues.extend(
                self._collect_action_configuration_issues(
                    action.type,
                    action.config if isinstance(action.config, dict) else {},
                    f"Action step {index}",
                )
            )

        if issues:
            detail = "Workflow configuration incomplete. " + " ".join(issues)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    def activate_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        self._validate_workflow_configuration(workflow)

        workflow.is_active = True

        if self._is_scheduled_trigger(workflow):
            workflow.next_run_at = self.next_run_from_cron(
                workflow.schedule_cron
            )
        else:
            workflow.next_run_at = None

        self.db.commit()

        return self.get_workflow(user, workflow_id)

    def deactivate_workflow(self, user: User, workflow_id: UUID) -> Workflow:
        workflow = self.get_workflow(user, workflow_id)
        workflow.is_active = False
        workflow.next_run_at = None
        self.db.commit()
        return self.get_workflow(user, workflow_id)

    def manual_run_workflow(
        self,
        user: User,
        workflow_id: UUID,
        payload: dict[str, Any] | None = None,
        *,
        commit: bool = True,
    ) -> WorkflowRun:
        workflow = self.get_workflow(user, workflow_id)

        if not workflow.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow must be active before manual run.",
            )

        self._validate_workflow_configuration(workflow)

        run = self._execute_workflow(
            workflow,
            workflow.triggers[0].type if workflow.triggers else WorkflowTriggerType.WEBHOOK_RECEIVED,
            payload or {"manual": True},
        )

        if commit:
            self.db.commit()
        else:
            self.db.flush()

        self.db.refresh(run)
        return run

    def list_runs(self, user: User, workflow_id: UUID, page: int, page_size: int) -> WorkflowRunListResponse:
        workflow = self.get_workflow(user, workflow_id)
        page, page_size = self._normalize_pagination(page, page_size)
        base = select(WorkflowRun).where(WorkflowRun.workflow_id == workflow.id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(WorkflowRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return WorkflowRunListResponse(
           items=list(items),
           pagination={
              "page": page,
              "page_size": page_size,
              "total": int(total),
              "total_pages": (int(total) + page_size - 1) // page_size if page_size else 0,
    },
)

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
        return PublicWorkflowWebhookResponse(
    message="Workflow executed successfully",
    workflow_run_id=run.id
)

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
            matching_trigger = next(
                (trigger for trigger in workflow.triggers if trigger.type == trigger_type),
                None,
            )

            if matching_trigger is not None and not self._trigger_matches(matching_trigger.config or {}, payload):
                continue

            self._execute_workflow(workflow, trigger_type, payload)
        if workflows:
            self.db.commit()
    def run_due_retries(self, limit: int = 25) -> dict[str, int]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        due_run_ids = self.db.scalars(
            select(WorkflowRun.id)
            .where(
                WorkflowRun.status == WorkflowRunStatus.FAILED,
                WorkflowRun.is_dead_letter.is_(False),
                WorkflowRun.next_retry_at.is_not(None),
                WorkflowRun.next_retry_at <= now,
            )
            .order_by(WorkflowRun.next_retry_at.asc())
            .limit(limit)
        ).all()

        # End the initial read transaction before claiming rows individually.
        self.db.rollback()

        retried = 0
        failed = 0

        for run_id in due_run_ids:
            try:
                previous_run = self.db.scalar(
                    select(WorkflowRun)
                    .options(
                        selectinload(WorkflowRun.workflow).selectinload(
                            Workflow.triggers
                        ),
                        selectinload(WorkflowRun.workflow).selectinload(
                            Workflow.actions
                        ),
                    )
                    .where(
                        WorkflowRun.id == run_id,
                        WorkflowRun.status == WorkflowRunStatus.FAILED,
                        WorkflowRun.is_dead_letter.is_(False),
                        WorkflowRun.next_retry_at.is_not(None),
                        WorkflowRun.next_retry_at <= now,
                    )
                    .with_for_update(skip_locked=True)
                )

                if previous_run is None:
                    self.db.rollback()
                    continue

                workflow = previous_run.workflow
                trigger_payload = previous_run.trigger_payload or {}
                trigger_type_value = (
                    trigger_payload.get("trigger_type")
                    or WorkflowTriggerType.WEBHOOK_RECEIVED.value
                )
                payload = trigger_payload.get("payload") or {}

                attempt_count = (previous_run.retry_count or 0) + 1

                retry_run = self._execute_workflow(
                    workflow,
                    WorkflowTriggerType(trigger_type_value),
                    payload,
                )

                retry_run.retry_count = attempt_count
                retry_run.max_retries = previous_run.max_retries

                # The previous failed attempt has been consumed.
                # It is no longer retryable, but it is not itself a dead letter;
                # the newest retry run carries the final retry/dead-letter state.
                previous_run.is_dead_letter = False
                previous_run.next_retry_at = None
                self.db.add(previous_run)

                if retry_run.status == WorkflowRunStatus.COMPLETED:
                    retry_run.next_retry_at = None
                    retry_run.is_dead_letter = False
                    retried += 1
                else:
                    if attempt_count >= retry_run.max_retries:
                        retry_run.is_dead_letter = True
                        retry_run.next_retry_at = None
                    else:
                        retry_run.is_dead_letter = False
                        retry_run.next_retry_at = (
                            datetime.now(timezone.utc)
                            + timedelta(minutes=attempt_count)
                        )

                    failed += 1

                self.db.add(retry_run)
                self.db.commit()

            except Exception as exc:
                self.db.rollback()

                try:
                    failed_run = self.db.scalar(
                        select(WorkflowRun)
                        .where(
                            WorkflowRun.id == run_id,
                            WorkflowRun.status == WorkflowRunStatus.FAILED,
                            WorkflowRun.is_dead_letter.is_(False),
                            WorkflowRun.next_retry_at.is_not(None),
                            WorkflowRun.next_retry_at <= now,
                        )
                        .with_for_update(skip_locked=True)
                    )

                    if failed_run is not None:
                        failed_run.retry_count = (
                            failed_run.retry_count or 0
                        ) + 1
                        failed_run.last_error = str(exc)

                        if failed_run.retry_count >= failed_run.max_retries:
                            failed_run.is_dead_letter = True
                            failed_run.next_retry_at = None
                        else:
                            failed_run.next_retry_at = (
                                datetime.now(timezone.utc)
                                + timedelta(minutes=failed_run.retry_count)
                            )

                        self.db.add(failed_run)
                        self.db.commit()
                    else:
                        self.db.rollback()

                except Exception:
                    self.db.rollback()
                    logger.exception(
                        "Failed to persist retry failure state: %s",
                        run_id,
                    )

                failed += 1
                logger.exception("Workflow retry failed: %s", run_id)

        return {
            "checked": len(due_run_ids),
            "retried": retried,
            "failed": failed,
        }

    def _trigger_matches(self, config: dict[str, Any], payload: dict[str, Any]) -> bool:
        if not config:
            return True

        from_email = str(payload.get("from") or payload.get("email") or "").lower()
        subject = str(payload.get("subject") or "").lower()
        body = str(payload.get("body") or payload.get("snippet") or "").lower()
        labels = [str(label).lower() for label in payload.get("label_ids", payload.get("labels", [])) or []]
        has_attachment = bool(payload.get("has_attachment") or payload.get("attachments"))

        expected_from = str(config.get("from_email") or "").strip().lower()
        if expected_from and expected_from not in from_email:
            return False

        subject_contains = str(config.get("subject_contains") or "").strip().lower()
        if subject_contains and subject_contains not in subject:
            return False

        body_contains = str(config.get("body_contains") or "").strip().lower()
        if body_contains and body_contains not in body:
            return False

        label = str(config.get("label") or config.get("label_id") or "").strip().lower()
        if label and label not in labels:
            return False

        if config.get("has_attachment") is True and not has_attachment:
            return False

        if config.get("unread_only") is True and "unread" not in labels:
            return False

        return True

    def _execute_workflow(self, workflow: Workflow, trigger_type: WorkflowTriggerType, payload: dict[str, Any]) -> WorkflowRun:
        owner = self.db.get(User, workflow.user_id)
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow owner not found.",
            )

        enforce_monthly_run_limit(self.db, owner)

        run = WorkflowRun(
            workflow_id=workflow.id,
            status=WorkflowRunStatus.RUNNING,
            trigger_payload={"trigger_type": trigger_type.value, "payload": payload},
            logs={"steps": []},
        )
        self.db.add(run)
        self.db.flush()

        logs: list[dict[str, Any]] = []
        payload.setdefault("action_results", [])
        payload.setdefault("actions", {})

        try:
            for action in workflow.actions:
                result = self._execute_action(workflow, action, payload)

                if action.type == WorkflowActionType.CONDITION:
                    branch_actions = (
                        action.config.get("on_true", [])
                        if result.get("matched")
                        else action.config.get("on_false", [])
                    )

                    branch_results = []
                    for branch_action in branch_actions:
                        branch_result = self._execute_action(
                            workflow,
                            WorkflowAction(
                                type=WorkflowActionType(branch_action["type"]),
                                config=branch_action.get("config", {}),
                            ),
                            payload,
                        )
                        branch_results.append(branch_result)

                    result["branch_results"] = branch_results

                if action.type == WorkflowActionType.OPENAI_TEXT_GENERATE:
                    usage = result.get("usage") or {}

                    payload["ai_output"] = result.get("output", "")
                    payload["ai_model"] = result.get("model", "")
                    payload["ai_total_tokens"] = usage.get("total_tokens", 0)
                    payload["ai_prompt_tokens"] = usage.get("prompt_tokens", 0)
                    payload["ai_completion_tokens"] = usage.get("completion_tokens", 0)

                payload["last_action_result"] = result
                payload["action_results"].append(result)
                payload["actions"][action.type.value] = result

                logs.append({
                    "action": action.type.value,
                    "status": "success",
                    "result": result,
                })

            run.status = WorkflowRunStatus.COMPLETED
        except Exception as exc:
            logs.append({"status": "failed", "error": str(exc)})

            run.status = WorkflowRunStatus.FAILED
            run.last_error = str(exc)
            run.retry_count = (run.retry_count or 0) + 1

            if run.retry_count >= run.max_retries:
                run.is_dead_letter = True
                run.next_retry_at = None
            else:
                from datetime import datetime, timedelta, timezone
                run.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    minutes=run.retry_count
                )

        run.logs = {"steps": logs}
        return run

    def _execute_action(self, workflow: Workflow, action: WorkflowAction, payload: dict[str, Any]) -> dict[str, Any]:
        if action.type == WorkflowActionType.SEND_WEBHOOK:
            url = self._render_value(
                action.config["url"],
                payload,
            ).strip()

            response = safe_outbound_request(
                method="POST",
                url=url,
                json_body={
                    "workflow_id": str(workflow.id),
                    "payload": payload,
                },
            )

            return {
                "status_code": response.status_code,
                "ok": response.ok,
            }

        if action.type == WorkflowActionType.SEND_EMAIL:
            to_email = self._render_value(action.config["to"], payload)
            subject = self._render_value(action.config["subject"], payload)
            body = self._render_value(action.config["body"], payload)
            return EmailService().send_email(to_email=to_email, subject=subject, body=body)

        if action.type == WorkflowActionType.HTTP_REQUEST:
            method = str(
                action.config.get("method", "POST")
            ).strip().upper()
            url = self._render_value(
                str(action.config.get("url", "")),
                payload,
            ).strip()
            headers = action.config.get("headers") or {}
            body = action.config.get("body")

            if isinstance(headers, dict):
                headers = {
                    str(key): self._render_value(
                        str(value),
                        payload,
                    )
                    for key, value in headers.items()
                }

            if isinstance(body, dict):
                body = {
                    key: self._render_value(str(value), payload)
                    for key, value in body.items()
                }

            if not url:
                raise ValueError(
                    "HTTP_REQUEST action requires config.url"
                )

            response = safe_outbound_request(
                method=method,
                url=url,
                headers=headers if isinstance(headers, dict) else None,
                json_body=body if method != "GET" else None,
                query_params=(
                    body
                    if method == "GET" and isinstance(body, dict)
                    else None
                ),
            )

            return {
                "status": "completed",
                "method": method,
                "url": sanitized_url_for_result(url),
                "status_code": response.status_code,
                "ok": response.ok,
                "response": (
                    response.text[:2000]
                    if response.text
                    else ""
                ),
            }
        if action.type == WorkflowActionType.GOOGLE_SHEETS_APPEND:
            import os

            spreadsheet_id = action.config.get("spreadsheet_id")
            sheet_name = action.config.get("sheet_name", "Sheet1")

            if not spreadsheet_id:
                raise ValueError("GOOGLE_SHEETS_APPEND requires config.spreadsheet_id")

            credentials_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
            if not credentials_path:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE not configured")

            creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )

            service = build("sheets", "v4", credentials=creds)

            row = [
            str(payload.get("name", "")),
            str(payload.get("email", "")),
            str(payload.get("phone", "")),
            str(payload.get("source", "")),
            ]

            response = (
            service.spreadsheets()
            .values()
            .append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:D",
            valueInputOption="RAW",
            body={"values": [row]},
            )
            .execute()
            )

            return {
                "status": "success",
                "spreadsheet_id": spreadsheet_id,
                "updated_range": response.get("updates", {}).get("updatedRange"),
            }




            return {
            "status": "completed",
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "ok": response.ok,
            "response": response.text[:2000] if response.text else "",
            }

        if action.type == WorkflowActionType.SLACK_SEND_MESSAGE:
            credential = (
                self.db.query(IntegrationCredential)
                .filter(
                    IntegrationCredential.tenant_id == workflow.tenant_id,
                    IntegrationCredential.provider == "slack",
                    IntegrationCredential.status == "connected",
                    IntegrationCredential.access_token_encrypted.isnot(None),
                )
                .first()
            )

            if credential is None:
                raise ValueError("Slack workspace is not connected.")

            token = decrypt_secret(credential.access_token_encrypted)
            if not token:
                raise ValueError("Slack access token is missing.")

            channel = self._render_value(
                str(action.config.get("channel") or action.config.get("channel_id") or ""),
                payload,
            ).strip()

            if not channel:
                raise ValueError("SLACK_SEND_MESSAGE requires config.channel or config.channel_id")

            message = self._render_value(
                str(action.config.get("message") or action.config.get("text") or ""),
                payload,
            ).strip()

            if not message:
                raise ValueError("SLACK_SEND_MESSAGE requires config.message")

            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "channel": channel,
                    "text": message,
                },
                timeout=20,
            )

            data = response.json()

            if response.status_code >= 400 or not data.get("ok"):
                raise ValueError(f"Slack send message failed: {data}")

            return {
                "status": "completed",
                "provider": "slack",
                "workspace": credential.account_email,
                "channel": channel,
                "message_ts": data.get("ts"),
                "ok": data.get("ok"),
            }

        if action.type == WorkflowActionType.OPENAI_TEXT_GENERATE:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured.")

            prompt = self._render_value(
                str(action.config.get("prompt") or ""),
                payload,
            ).strip()

            if not prompt:
                raise ValueError("OPENAI_TEXT_GENERATE requires config.prompt")

            model = str(action.config.get("model") or settings.OPENAI_MODEL or "gpt-4o-mini").strip()
            temperature = float(action.config.get("temperature", 0.3))
            max_tokens = int(action.config.get("max_tokens", 500))
            ai_memory_items = []
            for item in payload.get("action_results", []):
                if isinstance(item, dict) and item.get("provider") == "openai" and item.get("output"):
                    ai_memory_items.append(str(item.get("output")))

            ai_memory_context = ""
            if ai_memory_items:
                ai_memory_context = "\n\nPrevious AI outputs in this workflow:\n" + "\n".join(
                    f"{index + 1}. {value}"
                    for index, value in enumerate(ai_memory_items[-5:])
                )

            final_prompt = prompt + ai_memory_context

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an automation assistant inside NeuralShieldDigital. Return concise, useful output.",
                        },
                        {
                            "role": "user",
                            "content": final_prompt,
                        },
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=45,
            )

            data = response.json()

            if response.status_code >= 400:
                raise ValueError(f"OpenAI request failed: {data}")

            output_text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if not output_text:
                raise ValueError("OpenAI returned an empty response.")

            return {
                "status": "completed",
                "provider": "openai",
                "model": model,
                "output": output_text,
                "usage": data.get("usage"),
                "memory_items_used": len(ai_memory_items),
            }

        if action.type == WorkflowActionType.CREATE_LEAD:
            email = self._render_value(
                action.config.get("email", "{{email}}"),
                payload,
            ).strip().lower()

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

        if action.type == WorkflowActionType.UPDATE_LEAD:
            email = self._render_value(action.config.get("email", "{{email}}"), payload).strip().lower()
            if not email:
                raise ValueError("UPDATE_LEAD action resolved an empty email.")

            tags = self._render_tags(
                action.config.get("tags", payload.get("tags", [])),
                payload,
            )

            lead, created = LeadService(self.db).upsert_lead(
                user_id=workflow.user_id,
                tenant_id=workflow.tenant_id,
                name=self._render_optional_value(action.config.get("name"), payload),
                email=email,
                phone=self._render_optional_value(action.config.get("phone"), payload),
                source=self._render_optional_value(action.config.get("source"), payload),
                tags=tags,
                metadata={"workflow_id": str(workflow.id), "payload": payload, "updated_by": "workflow"},
            )

            return {
                "lead_id": str(lead.id),
                "email": lead.email,
                "created": created,
                "updated": not created,
                "tags": tags,
            }

        if action.type == WorkflowActionType.TAG_LEAD:
            email = self._render_value(action.config.get("email", "{{email}}"), payload).strip().lower()
            if not email:
                raise ValueError("TAG_LEAD action resolved an empty email.")

            tags = self._render_tags(action.config.get("tags", ["tagged", "workflow"]), payload)

            lead, created = LeadService(self.db).upsert_lead(
                user_id=workflow.user_id,
                tenant_id=workflow.tenant_id,
                name=self._render_optional_value(action.config.get("name", "{{name}}"), payload),
                email=email,
                phone=self._render_optional_value(action.config.get("phone"), payload),
                source=self._render_optional_value(action.config.get("source", "{{source}}"), payload),
                tags=tags,
                metadata={"workflow_id": str(workflow.id), "payload": payload, "tagged_by": "workflow"},
            )

            return {
                "lead_id": str(lead.id),
                "email": lead.email,
                "created": created,
                "tagged": True,
                "tags": tags,
            }

        if action.type == WorkflowActionType.WAIT:
            import time

            seconds = action.config.get("seconds")

            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, int)
                or seconds < 1
                or seconds > MAX_SYNC_WAIT_SECONDS
            ):
                raise ValueError(
                    "WAIT action requires integer config.seconds "
                    f"between 1 and {MAX_SYNC_WAIT_SECONDS}."
                )

            time.sleep(seconds)
            return {"waited_seconds": seconds, "status": "completed"}

        if action.type == WorkflowActionType.CONDITION:
            condition = action.config.get("condition")

            if condition is not None:
                if not isinstance(condition, bool):
                    raise ValueError(
                        "CONDITION config.condition must be a boolean."
                    )
                result = condition
            else:
                left_value = (
                    action.config["left"]
                    if "left" in action.config
                    else action.config.get("field")
                )
                right_value = (
                    action.config["right"]
                    if "right" in action.config
                    else action.config.get("value")
                )
                operator = str(
                    action.config.get("operator") or ""
                ).strip().lower()

                left = self._render_value(left_value, payload)
                right = self._render_value(right_value, payload)

                if operator in ("equals", "eq", "=="):
                    result = left == right
                elif operator in ("not_equals", "neq", "!="):
                    result = left != right
                elif operator == "contains":
                    result = right in left
                elif operator == "not_contains":
                    result = right not in left
                elif operator in ("greater_than", "gt", ">"):
                    try:
                        result = float(left) > float(right)
                    except (TypeError, ValueError) as error:
                        raise ValueError(
                            "CONDITION greater-than comparison "
                            "requires numeric values."
                        ) from error
                elif operator in ("less_than", "lt", "<"):
                    try:
                        result = float(left) < float(right)
                    except (TypeError, ValueError) as error:
                        raise ValueError(
                            "CONDITION less-than comparison "
                            "requires numeric values."
                        ) from error
                else:
                    raise ValueError(
                        f"Unsupported CONDITION operator: {operator}"
                    )

            return {
                "status": "success",
                "action_type": "CONDITION",
                "condition_result": result,
                "matched": result,
            }

        if action.type == WorkflowActionType.ADD_AUDIT_LOG:
            audit = AuditLog(
                user_id=workflow.user_id,
                action=action.config["action"],
                metadata={
                    "workflow_id": str(workflow.id),
                    "payload": payload,
                    "config": action.config,
                },
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
        clean_trigger = dict(trigger)
        if hasattr(clean_trigger.get("type"), "value"):
            clean_trigger["type"] = clean_trigger["type"].value

        clean_actions = []
        for action in actions:
            clean_action = dict(action)
            if hasattr(clean_action.get("type"), "value"):
                clean_action["type"] = clean_action["type"].value
            clean_actions.append(clean_action)

        return {"trigger": clean_trigger, "actions": clean_actions}

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
