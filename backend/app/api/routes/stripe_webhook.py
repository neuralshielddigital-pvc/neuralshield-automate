import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app.api.deps import db_session
from app.services.stripe_service import StripeService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
    db: Session = Depends(db_session),
) -> JSONResponse:
    logger.info("Stripe webhook received; starting raw body read")

    try:
        payload = await request.body()
        logger.info("Stripe webhook raw body read complete; bytes=%s", len(payload))
    except ClientDisconnect:
        logger.warning("Stripe webhook client disconnected while reading raw body")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"received": False, "processed": False, "error": "Client disconnected while reading webhook body."},
        )

    try:
        logger.info("Stripe webhook processing started")
        result = StripeService(db).handle_webhook_event(payload, stripe_signature)
        logger.info(
            "Stripe webhook processing completed; event_id=%s processed=%s",
            result.get("event_id"),
            result.get("processed"),
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook signature verification failed")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"received": False, "processed": False, "error": "Invalid Stripe webhook signature."},
        )
    except HTTPException as exc:
        logger.warning("Stripe webhook rejected; status=%s detail=%s", exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"received": False, "processed": False, "error": exc.detail},
        )
    except Exception:
        logger.exception("Unexpected Stripe webhook processing error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"received": False, "processed": False, "error": "Internal webhook processing error."},
        )
