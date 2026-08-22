from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.integrations.google.gmail import GmailService
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.config import settings
from app.core.encryption import encrypt_secret
from app.integrations.google.oauth import SCOPES, build_google_oauth_url
from app.models.integration import IntegrationCredential
from app.models.user import User

router = APIRouter(prefix="/integrations/google", tags=["Google Integrations"])
UTC = timezone.utc

REQUIRED_GMAIL_SCOPES = {
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
}


def _create_oauth_state(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "provider": "google",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_oauth_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.") from exc

    if payload.get("provider") != "google":
        raise HTTPException(status_code=400, detail="Invalid OAuth provider state.")

    return payload


@router.get("/connect")
def connect_google(current_user: User = Depends(get_current_user)):
    state = _create_oauth_state(current_user)
    return {"authorization_url": build_google_oauth_url(state), "state": state}


@router.get("/callback")
def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(db_session),
):
    state_payload = _decode_oauth_state(state)
    tenant_id = UUID(state_payload["tenant_id"])
    user_id = UUID(state_payload["sub"])

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    if token_response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Google token exchange failed.",
                "google_response": token_response.text,
            },
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    scope = token_data.get("scope", " ".join(SCOPES))

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="Google did not return an access token.",
        )

    granted_scopes = {
        item.strip()
        for item in str(scope).split()
        if item.strip()
    }
    missing_scopes = REQUIRED_GMAIL_SCOPES - granted_scopes

    if missing_scopes:
        missing_list = ", ".join(sorted(missing_scopes))

        raise HTTPException(
            status_code=400,
            detail=(
                "Google connection is missing required Gmail permissions. "
                "Remove the existing Google connection, reconnect, and allow "
                f"all Gmail permissions. Missing scopes: {missing_list}"
            ),
        )

    account_email = None
    userinfo_response = requests.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if userinfo_response.status_code < 400:
        account_email = userinfo_response.json().get("email")

    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))

    existing = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == tenant_id,
            IntegrationCredential.provider == "google",
            IntegrationCredential.account_email == account_email,
        )
        .first()
    )

    credential = existing or IntegrationCredential(
        tenant_id=tenant_id,
        user_id=user_id,
        provider="google",
    )

    credential.account_email = account_email
    credential.access_token_encrypted = encrypt_secret(access_token)
    if refresh_token:
        credential.refresh_token_encrypted = encrypt_secret(refresh_token)
    credential.token_expires_at = token_expires_at
    credential.scopes = scope
    credential.status = "connected"

    db.add(credential)
    db.flush()

    # A reconnect must leave only one active Google credential for the
    # same tenant/account. Historical credentials are retained for audit
    # purposes but must not continue to be polled.
    if account_email:
        (
            db.query(IntegrationCredential)
            .filter(
                IntegrationCredential.tenant_id == tenant_id,
                IntegrationCredential.provider == "google",
                IntegrationCredential.account_email == account_email,
                IntegrationCredential.id != credential.id,
                IntegrationCredential.status == "connected",
            )
            .update(
                {"status": "disconnected"},
                synchronize_session=False,
            )
        )

    db.commit()

    return RedirectResponse(
        url=(
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
            "/dashboard/integrations?google=connected"
        ),
        status_code=302,
    )

@router.get("/gmail/profile")
def gmail_profile(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "google",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        raise HTTPException(
            status_code=404,
            detail="Google account is not connected.",
        )

    gmail = GmailService(credential)

    return gmail.profile()

@router.delete("/disconnect")
def disconnect_google(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "google",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        return {
            "success": True,
            "provider": "google",
            "status": "not_connected",
            "message": "Google account was already disconnected.",
        }

    credential.status = "disconnected"
    credential.access_token_encrypted = None
    credential.refresh_token_encrypted = None
    credential.token_expires_at = None

    db.add(credential)
    db.commit()

    return {
        "success": True,
        "provider": "google",
        "status": "disconnected",
        "message": "Google account disconnected successfully.",
    }

@router.get("/gmail/messages/latest")
def gmail_latest_messages(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "google",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        raise HTTPException(status_code=404, detail="Google account is not connected.")

    gmail = GmailService(credential)

    return gmail.latest_messages(max_results=10)

@router.get("/gmail/messages/{message_id}")
def gmail_message(
    message_id: str,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    credential = (
        db.query(IntegrationCredential)
        .filter(
            IntegrationCredential.tenant_id == current_user.tenant_id,
            IntegrationCredential.provider == "google",
            IntegrationCredential.status == "connected",
        )
        .first()
    )

    if credential is None:
        raise HTTPException(
            status_code=404,
            detail="Google account is not connected.",
        )

    gmail = GmailService(credential)

    return gmail.message(message_id)
