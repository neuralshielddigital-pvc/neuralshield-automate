from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = getattr(settings, "INTEGRATION_ENCRYPTION_KEY", None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integration encryption key is not configured.",
        )
    return Fernet(key.encode())


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _get_fernet().decrypt(value.encode()).decode()
