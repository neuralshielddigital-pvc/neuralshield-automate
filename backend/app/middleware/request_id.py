from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(settings.REQUEST_ID_HEADER) or f"req_{uuid4().hex}"
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[settings.REQUEST_ID_HEADER] = request_id
        return response
