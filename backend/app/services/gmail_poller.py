from __future__ import annotations

import logging
from email.utils import parseaddr
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.google.gmail import GmailService
from app.models.enums import WorkflowTriggerType
from app.models.integration import IntegrationCredential
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


def _header(headers: list[dict[str, Any]], name: str) -> str:
    for item in headers:
        if item.get("name", "").lower() == name.lower():
            return str(item.get("value") or "")
    return ""


def _gmail_payload(message: dict[str, Any], account_email: str) -> dict[str, Any]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []

    raw_from = _header(headers, "From")
    from_email = parseaddr(raw_from)[1] or raw_from
    subject = _header(headers, "Subject")
    snippet = message.get("snippet") or ""

    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "from": from_email,
        "from_raw": raw_from,
        "to": account_email,
        "subject": subject,
        "snippet": snippet,
        "body": snippet,
        "label_ids": message.get("labelIds") or [],
        "source": "gmail",
    }


def run_gmail_new_email_poll(db: Session, max_messages: int = 5) -> dict[str, int]:
    connected_credentials = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.provider == "google",
            IntegrationCredential.status == "connected",
            IntegrationCredential.access_token_encrypted.isnot(None),
        )
        .order_by(
            IntegrationCredential.updated_at.desc(),
            IntegrationCredential.created_at.desc(),
        )
        .all()
    )

    # Defensive dedupe: legacy reconnects may have left multiple connected
    # rows for the same tenant/account. Poll only the newest one.
    credentials = []
    seen_accounts = set()

    for credential in connected_credentials:
        account_key = (
            str(credential.tenant_id),
            (credential.account_email or "").strip().lower(),
        )
        if account_key in seen_accounts:
            continue
        seen_accounts.add(account_key)
        credentials.append(credential)

    checked = 0
    triggered = 0
    failed = 0

    for credential in credentials:
        checked += 1
        try:
            # Copy the JSONB value before mutation so SQLAlchemy detects
            # and persists the updated sync state.
            sync_state = dict(credential.sync_state or {})
            seen_message_ids = list(
                sync_state.get("gmail_seen_message_ids") or []
            )
            seen_ids = set(seen_message_ids)

            gmail = GmailService(credential)
            latest = gmail.latest_messages(max_results=max_messages)
            messages = latest.get("messages") or []

            new_ids = [
                item["id"]
                for item in messages
                if item.get("id") and item["id"] not in seen_ids
            ]

            for message_id in reversed(new_ids):
                raw_message = gmail.message(message_id)
                payload = _gmail_payload(raw_message, credential.account_email or "")

                WorkflowService(db).execute_tenant_trigger(
                    credential.tenant_id,
                    WorkflowTriggerType.GMAIL_NEW_EMAIL,
                    payload,
                )

                triggered += 1
                seen_ids.add(message_id)
                seen_message_ids.append(message_id)

            # Preserve processing order and retain only the newest 200 IDs.
            sync_state["gmail_seen_message_ids"] = seen_message_ids[-200:]
            credential.sync_state = sync_state
            db.add(credential)
            db.commit()

        except Exception:
            db.rollback()
            failed += 1
            logger.exception(
                "Gmail poller failed for credential_id=%s tenant_id=%s account_email=%s",
                credential.id,
                credential.tenant_id,
                credential.account_email,
            )

    return {"checked": checked, "triggered": triggered, "failed": failed}
