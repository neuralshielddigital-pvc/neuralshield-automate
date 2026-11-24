"""Automation-specific hosted checkout and independently verified webhooks."""
from datetime import datetime, timezone
import hashlib
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.automation_whop import AutomationWhopEvent
from app.services.automation_whop_service import AutomationWhopService, adapter, owned_memberships
from app.services.automation_whop_transport import WhopError, WhopUnavailable, MAX_BODY, verify_notice, object_value, identifier
from app.services.automation_whop_catalog import binding_for

router = APIRouter(tags=["automation-whop"])


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_name: str
    command_id: UUID


def enabled():
    if not settings.AUTOMATION_WHOP_ENABLED:
        raise HTTPException(503, "Whop billing is being configured. Please contact support.")


@router.post("/whop/checkout")
def checkout(payload: CheckoutRequest, user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    enabled()
    try:
        with httpx.Client(trust_env=False) as client:
            return AutomationWhopService(db, adapter(client)).checkout(user, payload.plan_name, payload.command_id)
    except WhopError:
        db.rollback()
        raise HTTPException(409, "Checkout could not be verified. Contact support.") from None
    except WhopUnavailable:
        db.rollback()
        raise HTTPException(503, "Billing provider is temporarily unavailable. Retry this checkout later.") from None


@router.post("/whop/refresh")
def refresh(user: User = Depends(get_current_user), db: Session = Depends(db_session)):
    enabled()
    now = datetime.now(timezone.utc)
    try:
        with httpx.Client(trust_env=False) as client:
            service = AutomationWhopService(db, adapter(client))
            for row in owned_memberships(db, user):
                if (now - row.checked_at.replace(tzinfo=timezone.utc)).total_seconds() < 60:
                    continue
                service.refresh_membership(row.membership_id, now)
            db.commit()
        return {"refreshed": True}
    except (WhopError, WhopUnavailable):
        db.rollback()
        raise HTTPException(503, "Subscription verification is pending. Please retry shortly.") from None


@router.post("/webhooks/automation/whop")
async def webhook(request: Request, db: Session = Depends(db_session)):
    enabled()
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY:
            raise HTTPException(413, "Webhook too large.")
    try:
        notice = verify_notice(bytes(raw), dict(request.headers), settings.AUTOMATION_WHOP_WEBHOOK_SECRET,
            settings.AUTOMATION_WHOP_ACCOUNT_ID, now=int(time.time()))
    except WhopError:
        raise HTTPException(400, "Invalid Whop webhook.") from None
    digest = hashlib.sha256(raw).hexdigest()
    try:
        if db.get_bind().dialect.name == "postgresql":
            key = int.from_bytes(hashlib.sha256(notice.event_id.encode()).digest()[:8], "big", signed=True)
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        saved = db.get(AutomationWhopEvent, notice.event_id)
        if saved:
            if saved.body_hash != digest:
                raise HTTPException(409, "Webhook identifier conflict.")
            return {"received": True}
        with httpx.Client(trust_env=False) as client:
            provider = adapter(client)
            service = AutomationWhopService(db, provider)
            now = datetime.now(timezone.utc)
            is_member = notice.event_type.startswith("membership.")
            resource = provider.retrieve("memberships" if is_member else "payments", notice.resource_id)
            merchant = object_value(resource.get("account")).get("id") if is_member else resource.get("account_id")
            if merchant != settings.AUTOMATION_WHOP_ACCOUNT_ID:
                raise WhopError("merchant_mismatch")
            products = {binding_for(code, settings).product_id for code in ("starter", "pro", "business")}
            if identifier(resource.get("product_id"), "prod_") not in products:
                # A shared merchant also sells Agency and Client Acquisition.
                # Independently identify unrelated products; never grant access.
                db.add(AutomationWhopEvent(event_id=notice.event_id, body_hash=digest, handled_at=now))
                db.commit()
                return {"received": True, "ignored": True}
            if is_member:
                service.refresh_membership(notice.resource_id, now)
            elif notice.event_type == "payment.succeeded":
                service.reconcile_payment(notice.resource_id, now)
            else:
                payment = provider.retrieve("payments", notice.resource_id)
                intent = service.resolve_intent(payment)
                # Failed renewals do not create access. Refresh an existing membership
                # to determine whether a previously paid period is still current.
                for member in owned_memberships(db, db.get(User, intent.user_id)):
                    service.refresh_membership(member.membership_id, now)
        db.add(AutomationWhopEvent(event_id=notice.event_id, body_hash=digest, handled_at=now))
        db.commit()  # Receipt and entitlement are one transaction, never early ACK.
        return {"received": True}
    except (WhopError, WhopUnavailable):
        db.rollback()
        raise HTTPException(503, "Whop verification pending; retry delivery.") from None
