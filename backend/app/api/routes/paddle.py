from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.services.paddle_service import PaddleService


router = APIRouter(prefix="/paddle", tags=["paddle"])


class PaddleCheckoutRequest(BaseModel):
    plan_name: str = Field(min_length=2, max_length=50)


class PaddleCheckoutResponse(BaseModel):
    transaction_id: str
    provider: str
    plan: str
    environment: str


@router.post("/checkout", response_model=PaddleCheckoutResponse)
def create_paddle_checkout(
    payload: PaddleCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> PaddleCheckoutResponse:
    result = PaddleService(db).create_transaction(
        current_user,
        payload.plan_name,
    )
    return PaddleCheckoutResponse(**result)
