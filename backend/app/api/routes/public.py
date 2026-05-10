from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.config import settings
from app.schemas.public import PublicLeadCreate, PublicLeadResponse
from app.services.public_lead_service import PublicLeadService


router = APIRouter(prefix="/public", tags=["public"])

_PUBLIC_LEAD_ATTEMPTS: dict[str, list[float]] = {}


def public_lead_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    now = monotonic()
    attempts = [
        timestamp
        for timestamp in _PUBLIC_LEAD_ATTEMPTS.get(client_host, [])
        if now - timestamp < settings.PUBLIC_LEAD_RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(attempts) >= settings.PUBLIC_LEAD_RATE_LIMIT:
        _PUBLIC_LEAD_ATTEMPTS[client_host] = attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please try again later.",
        )
    attempts.append(now)
    _PUBLIC_LEAD_ATTEMPTS[client_host] = attempts


@router.post("/leads", response_model=PublicLeadResponse, dependencies=[Depends(public_lead_rate_limit)])
def create_public_lead(
    payload: PublicLeadCreate,
    db: Session = Depends(db_session),
) -> PublicLeadResponse:
    return PublicLeadService(db).create_public_lead(payload)
