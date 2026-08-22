from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
@router.get("/")
def list_integrations(current_user: User = Depends(get_current_user)):
    return []


@router.delete("/{credential_id}")
def disconnect_integration(
    credential_id: str,
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "message": "Integration disconnect endpoint ready",
        "credential_id": credential_id,
    }
