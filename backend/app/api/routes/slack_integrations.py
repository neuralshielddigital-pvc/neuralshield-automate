from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import hashlib
import hmac
import time
from typing import Any

from fastapi import Request
from app.models.enums import WorkflowTriggerType
from app.services.workflow_service import WorkflowService

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.config import settings
from app.core.encryption import encrypt_secret
from app.models.integration import IntegrationCredential
from app.models.user import User

router = APIRouter(prefix="/integrations/slack", tags=["Slack Integrations"])
UTC = timezone.utc

SLACK_SCOPES = [
    "chat:write",
    "channels:read",
    "groups:read",
    "team:read",
    "users:read",
    "incoming-webhook",
]


def _create_oauth_state(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "provider": "slack",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.") from exc

    if payload.get("provider") != "slack":
        raise HTTPException(status_code=400, detail="Invalid OAuth provider state.")

    return payload


@router.get("/status")
def slack_status() -> dict:
    return {"provider": "slack", "status": "router_ready"}


@router.get("/connect")
def connect_slack(current_user: User = Depends(get_current_user)) -> dict:
    if not settings.SLACK_CLIENT_ID or not settings.SLACK_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Slack OAuth is not configured.")

    state = _create_oauth_state(current_user)

    authorization_url = "https://slack.com/oauth/v2/authorize?" + urlencode(
        {
            "client_id": settings.SLACK_CLIENT_ID,
            "scope": ",".join(SLACK_SCOPES),
            "redirect_uri": settings.SLACK_REDIRECT_URI,
            "state": state,
        }
    )

    return {"authorization_url": authorization_url, "state": state}


@router.get("/callback")
def slack_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(db_session),
) -> dict:
    if not settings.SLACK_CLIENT_ID or not settings.SLACK_CLIENT_SECRET or not settings.SLACK_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Slack OAuth is not configured.")

    state_payload = _decode_oauth_state(state)
    tenant_id = UUID(state_payload["tenant_id"])
    user_id = UUID(state_payload["sub"])

    token_response = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": settings.SLACK_CLIENT_ID,
            "client_secret": settings.SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.SLACK_REDIRECT_URI,
        },
        timeout=30,
    )

    token_data = token_response.json()

    if token_response.status_code >= 400 or not token_data.get("ok"):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Slack token exchange failed.",
                "slack_response": token_data,
            },
        )

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Slack did not return an access token.")

    team = token_data.get("team") or {}
    authed_user = token_data.get("authed_user") or {}
    incoming_webhook = token_data.get("incoming_webhook") or {}

    team_id = team.get("id")
    team_name = team.get("name") or team_id or "Slack Workspace"

    existing = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == tenant_id,
            IntegrationCredential.provider == "slack",
            IntegrationCredential.account_email == team_name,
        )
        .first()
    )

    credential = existing or IntegrationCredential(
        tenant_id=tenant_id,
        user_id=user_id,
        provider="slack",
    )

    credential.account_email = team_name
    credential.access_token_encrypted = encrypt_secret(access_token)
    credential.refresh_token_encrypted = None
    credential.token_expires_at = None
    credential.scopes = token_data.get("scope") or ",".join(SLACK_SCOPES)
    credential.status = "connected"
    credential.sync_state = {
        "team_id": team_id,
        "team_name": team_name,
        "bot_user_id": token_data.get("bot_user_id"),
        "authed_user_id": authed_user.get("id"),
        "incoming_webhook": incoming_webhook,
    }

    db.add(credential)
    db.commit()

    return {
        "success": True,
        "provider": "slack",
        "workspace": team_name,
        "message": "Slack workspace connected successfully.",
    }


@router.get("/profile")
def slack_profile(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "slack",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        raise HTTPException(status_code=404, detail="Slack workspace is not connected.")

    return {
        "provider": "slack",
        "status": credential.status,
        "workspace": credential.account_email,
        "scopes": credential.scopes,
        "sync_state": credential.sync_state,
        "connected_at": credential.created_at,
        "updated_at": credential.updated_at,
    }


@router.delete("/disconnect")
def disconnect_slack(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "slack",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        return {
            "success": True,
            "provider": "slack",
            "status": "not_connected",
            "message": "Slack workspace was already disconnected.",
        }

    credential.status = "disconnected"
    credential.access_token_encrypted = None
    credential.refresh_token_encrypted = None
    credential.token_expires_at = None

    db.add(credential)
    db.commit()

    return {
        "success": True,
        "provider": "slack",
        "status": "disconnected",
        "message": "Slack workspace disconnected successfully.",
    }

def _verify_slack_signature(request: Request, raw_body: bytes) -> None:
    signing_secret = settings.SLACK_SIGNING_SECRET

    if not signing_secret:
        raise HTTPException(status_code=500, detail="Slack signing secret is not configured.")

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    slack_signature = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not slack_signature:
        raise HTTPException(status_code=401, detail="Missing Slack signature headers.")

    try:
        request_timestamp = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Slack timestamp.") from exc

    if abs(time.time() - request_timestamp) > 60 * 5:
        raise HTTPException(status_code=401, detail="Slack request timestamp expired.")

    base_string = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        base_string,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, slack_signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature.")


def _slack_message_payload(event: dict[str, Any], team_id: str) -> dict[str, Any]:
    return {
        "source": "slack",
        "team_id": team_id,
        "channel_id": event.get("channel"),
        "user_id": event.get("user"),
        "text": event.get("text") or "",
        "message_ts": event.get("ts"),
        "event_ts": event.get("event_ts"),
        "thread_ts": event.get("thread_ts"),
    }


@router.post("/events")
async def slack_events(
    request: Request,
    db: Session = Depends(db_session),
) -> dict:
    raw_body = await request.body()
    _verify_slack_signature(request, raw_body)

    body = await request.json()

    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    if body.get("type") != "event_callback":
        return {"ok": True, "ignored": True, "reason": "unsupported_event_type"}

    event = body.get("event") or {}
    team_id = body.get("team_id") or event.get("team")

    if event.get("type") != "message":
        return {"ok": True, "ignored": True, "reason": "not_message_event"}

    if event.get("subtype"):
        return {"ok": True, "ignored": True, "reason": "message_subtype_ignored"}

    if not team_id:
        return {"ok": True, "ignored": True, "reason": "missing_team_id"}

    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.provider == "slack",
            IntegrationCredential.status == "connected",
        )
        .all()
    )

    matching_credential = None
    for item in credential:
        sync_state = item.sync_state or {}
        if sync_state.get("team_id") == team_id:
            matching_credential = item
            break

    if matching_credential is None:
        return {"ok": True, "ignored": True, "reason": "workspace_not_connected"}

    payload = _slack_message_payload(event, team_id)

    WorkflowService(db).execute_tenant_trigger(
        matching_credential.tenant_id,
        WorkflowTriggerType.SLACK_NEW_MESSAGE,
        payload,
    )

    return {
        "ok": True,
        "triggered": True,
        "trigger_type": "SLACK_NEW_MESSAGE",
    }
