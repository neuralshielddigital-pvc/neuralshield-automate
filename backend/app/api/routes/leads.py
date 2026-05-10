from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.campaign import (
    LeadCreate,
    LeadImportRequest,
    LeadImportResponse,
    LeadListResponse,
    LeadNotesUpdate,
    LeadRead,
    LeadStageUpdate,
    LeadUpdate,
)
from app.services.lead_service import LeadService


router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/import", response_model=LeadImportResponse, status_code=status.HTTP_201_CREATED)
def import_leads(
    payload: LeadImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadImportResponse:
    return LeadService(db).import_leads(current_user, payload)


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadRead:
    return LeadService(db).create_lead(current_user, payload)


@router.get("", response_model=LeadListResponse)
def list_leads(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadListResponse:
    return LeadService(db).list_leads(current_user, page, page_size, search)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadRead:
    return LeadService(db).get_lead(current_user, lead_id)


@router.patch("/{lead_id}/stage", response_model=LeadRead)
def update_lead_stage(
    lead_id: UUID,
    payload: LeadStageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadRead:
    return LeadService(db).update_stage(current_user, lead_id, payload)


@router.patch("/{lead_id}/notes", response_model=LeadRead)
def update_lead_notes(
    lead_id: UUID,
    payload: LeadNotesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadRead:
    return LeadService(db).update_notes(current_user, lead_id, payload)


@router.put("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> LeadRead:
    return LeadService(db).update_lead(current_user, lead_id, payload)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Response:
    LeadService(db).delete_lead(current_user, lead_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
