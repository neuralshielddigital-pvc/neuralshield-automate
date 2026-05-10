from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.deps import db_session
from fastapi import Depends


router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(db_session)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
