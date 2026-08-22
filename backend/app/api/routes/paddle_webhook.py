import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app.api.deps import db_session
from app.services.paddle_webhook_service import PaddleWebhookService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/paddle", tags=["paddle"])


@router.post("/webhook")
async def paddle_webhook(
    request: Request,
    signature: str | None = Header(
        default=None,
        alias="Paddle-Signature",
    ),
    db: Session = Depends(db_session),
) -> JSONResponse:
    try:
        payload = await request.body()
    except ClientDisconnect:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "received": False,
                "processed": False,
            },
        )

    try:
        result = PaddleWebhookService(db).handle_webhook_event(
            payload,
            signature,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result,
        )
    except HTTPException as exc:
        logger.warning(
            "Paddle webhook rejected: %s",
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "received": False,
                "processed": False,
                "error": exc.detail,
            },
        )
    except Exception:
        logger.exception("Unexpected Paddle webhook error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "received": False,
                "processed": False,
                "error": "Internal webhook processing error.",
            },
        )
