"""Agency-only signed Whop webhook; feature gated, no browser grants."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import db_session
from app.core.config import settings
from app.services.agency_whop_contract import validate_verified_whop_purchase
from app.services.agency_whop_event_envelope import MAX_EVENT_BYTES, parse_authenticated_whop_event
from app.services.agency_whop_persistence import AgencyWhopPersistence
from app.services.agency_whop_provider import WhopProvider, WhopUnavailable, verify_signature
from app.services.agency_whop_settings import configured_agency_whop_products

router = APIRouter(prefix="/webhooks/agency/whop", tags=["agency-whop"])


def process_event(event, product_map, db):
    provider = WhopProvider(settings.AGENCY_WHOP_API_KEY, settings.AGENCY_WHOP_ACCOUNT_ID)
    if event.event_type == "payment.succeeded":
        payment_id = event.data.get("id")
    elif event.event_type in ("refund.created", "refund.updated"):
        refund = provider.retrieve("refunds", event.data.get("id"))
        if refund.get("account_id") != settings.AGENCY_WHOP_ACCOUNT_ID:
            raise ValueError("Wrong refund merchant")
        if refund.get("status") != "succeeded":
            return {"handled": False}
        payment_id = refund.get("payment_id")
    else:
        return {"handled": False}
    facts, revoked = provider.purchase(payment_id)
    if facts.product_id not in product_map:
        return {"handled": False}
    if event.event_type.startswith("refund.") and not revoked:
        # Provider replicas may lag; ask Whop to retry rather than lose revocation.
        raise WhopUnavailable("Refund not reflected in payment")
    purchase = validate_verified_whop_purchase(
        independently_verified=True, payment_status=facts.status,
        provider_order_id=facts.order_id, provider_product_id=facts.product_id,
        configured_product_map=product_map, amount=facts.amount_usd,
        currency=facts.currency, customer_email=facts.customer_email,
    )
    return AgencyWhopPersistence(db).record_verified_purchase(purchase, revoked=revoked)


@router.post("")
async def webhook(request: Request, db: Session = Depends(db_session)):
    if not settings.AGENCY_WHOP_ENABLED:
        raise HTTPException(404, "Not found")
    try:
        product_map = configured_agency_whop_products()
        if not settings.AGENCY_WHOP_ACCOUNT_ID.startswith("biz_"):
            raise ValueError("Missing merchant")
    except ValueError:
        raise HTTPException(503, "Agency billing is not configured")
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > MAX_EVENT_BYTES:
            raise HTTPException(413, "Payload too large")
    try:
        verify_signature(bytes(payload), request.headers, settings.AGENCY_WHOP_WEBHOOK_SECRET)
        event = parse_authenticated_whop_event(bytes(payload), signature_verified=True)
        if event.event_id != request.headers.get("webhook-id"):
            raise ValueError("Event identity mismatch")
    except ValueError:
        raise HTTPException(400, "Invalid webhook")
    try:
        return await run_in_threadpool(process_event, event, product_map, db)
    except (WhopUnavailable, IntegrityError):
        raise HTTPException(503, "Retry delivery")
    except ValueError:
        raise HTTPException(422, "Purchase verification failed")
