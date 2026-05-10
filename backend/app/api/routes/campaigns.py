from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignRead,
    CampaignStatsResponse,
    CampaignUpdate,
)
from app.services.campaign_service import CampaignService


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignRead:
    return CampaignService(db).create_campaign(current_user, payload)


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    page: int = 1,
    page_size: int = 25,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignListResponse:
    return CampaignService(db).list_campaigns(current_user, page, page_size)


@router.get("/stats", response_model=CampaignStatsResponse)
def get_campaign_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignStatsResponse:
    return CampaignService(db).stats(current_user)


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignRead:
    return CampaignService(db).get_campaign(current_user, campaign_id)


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignRead:
    return CampaignService(db).update_campaign(current_user, campaign_id, payload)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Response:
    CampaignService(db).delete_campaign(current_user, campaign_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{campaign_id}/activate", response_model=CampaignRead)
def activate_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignRead:
    return CampaignService(db).activate_campaign(current_user, campaign_id)


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
def pause_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> CampaignRead:
    return CampaignService(db).pause_campaign(current_user, campaign_id)
