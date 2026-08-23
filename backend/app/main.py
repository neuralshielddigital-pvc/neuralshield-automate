import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_timeout import RequestTimeoutMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.background_worker import start_background_worker, stop_background_worker


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS or ["*"])
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestTimeoutMiddleware)
    cors_origins = list(settings.BACKEND_CORS_ORIGINS)
    if (
        settings.AGENCY_PILOT_ORIGIN
        and settings.AGENCY_PILOT_ORIGIN not in cors_origins
    ):
        cors_origins.append(settings.AGENCY_PILOT_ORIGIN)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", settings.REQUEST_ID_HEADER],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled request error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error.", "request_id": request_id},
        )

    @app.on_event("startup")
    async def startup_background_worker() -> None:
        start_background_worker()

    @app.on_event("shutdown")
    async def shutdown_background_worker() -> None:
        stop_background_worker()

    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_app()
