from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.security import generate_api_key, hash_api_key
from app.models.security import APIKey
from app.models.user import User

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str


@router.get("")
def list_api_keys(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
        .all()
    )

    return {
        "items": [
            {
                "id": str(key.id),
                "name": key.name,
                "status": "revoked" if key.revoked else "active",
                "is_active": not key.revoked,
                "created_at": key.created_at,
            }
            for key in keys
        ]
    }


@router.post("")
def create_api_key(
    payload: CreateAPIKeyRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    plaintext_key = generate_api_key()

    api_key = APIKey(
        user_id=current_user.id,
        name=payload.name.strip() or "Default API Key",
        key_hash=hash_api_key(plaintext_key),
        revoked=False,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "api_key": plaintext_key,
        "message": "Copy this API key now. It will not be shown again.",
        "created_at": api_key.created_at,
    }


@router.delete("/{api_key_id}")
def revoke_api_key(
    api_key_id: str,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    key = (
        db.query(APIKey)
        .filter(APIKey.id == api_key_id, APIKey.user_id == current_user.id)
        .first()
    )

    if key is None:
        return {"success": True, "message": "API key already revoked or not found."}

    key.revoked = True
    db.add(key)
    db.commit()

    return {"success": True, "message": "API key revoked successfully."}
