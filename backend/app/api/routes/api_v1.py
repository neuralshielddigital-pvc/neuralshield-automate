from fastapi import APIRouter, Depends

from app.api.deps import get_api_key_user
from app.models.user import User


router = APIRouter(prefix="/v1", tags=["API v1"])


@router.get("/me")
def api_v1_me(
    current_user: User = Depends(get_api_key_user),
) -> dict:
    return {
        "user_id": str(current_user.id),
        "tenant_id": (
            str(current_user.tenant_id)
            if current_user.tenant_id
            else None
        ),
        "email": current_user.email,
        "role": (
            current_user.role.value
            if current_user.role
            else None
        ),
        "api_version": "v1",
    }
