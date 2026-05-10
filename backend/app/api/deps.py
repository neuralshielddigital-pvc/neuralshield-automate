from collections.abc import Generator
from collections.abc import Callable
from time import monotonic
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
_LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(db_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
        parsed_user_id = UUID(user_id)
    except JWTError as exc:
        raise credentials_exception from exc
    except ValueError as exc:
        raise credentials_exception from exc

    user = db.get(User, parsed_user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return dependency


def login_rate_limit_ready(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    now = monotonic()
    attempts = [
        timestamp
        for timestamp in _LOGIN_ATTEMPTS.get(client_host, [])
        if now - timestamp < settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(attempts) >= settings.LOGIN_RATE_LIMIT:
        _LOGIN_ATTEMPTS[client_host] = attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    attempts.append(now)
    _LOGIN_ATTEMPTS[client_host] = attempts
    return None
