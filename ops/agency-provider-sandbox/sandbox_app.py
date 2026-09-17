"""Local owner-operated sandbox harness; never imported by the production app."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.deps import db_session
from app.api.routes.agency_member import router as member_router
from app.core.config import settings
from app.models.agency_commerce import (
    AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment,
    AgencyMemberAccessToken,
)
from app.models.system import WebhookEvent
from app.services.agency_commerce_service import AgencyCommerceService
from app.services.agency_delivery_service import AgencyDeliveryService
from app.services.paddle_webhook_service import PaddleWebhookService

PRICE = 'pri_01kzwq9m1s1m7ss5ds5exax1cb'
RECIPIENT = 'neuralshielddigital@gmail.com'
MEMBER_URL = 'http://localhost:8097/member/'
TABLES = (AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment,
          AgencyMemberAccessToken, WebhookEvent)
HERE = Path(__file__).resolve().parent


def validate_configuration(client_token):
    """Refuse any production or non-dedicated target before opening a database."""
    try:
        url = make_url(settings.DATABASE_URL)
        safe_db = (url.drivername == 'postgresql+psycopg'
                   and url.host == 'agency-sandbox-db'
                   and url.database == 'nsd_agency_test_provider'
                   and url.username == 'agency_test'
                   and not url.query and url.port in (None, 5432))
    except Exception:
        safe_db = False
    if (not safe_db or settings.ENVIRONMENT != 'test'
            or settings.PADDLE_ENVIRONMENT != 'sandbox'
            or settings.PADDLE_API_BASE_URL != 'https://sandbox-api.paddle.com'
            or settings.AGENCY_STARTER_SANDBOX_PRICE_ID != PRICE
            or settings.AGENCY_DELIVERY_TEST_RECIPIENT != RECIPIENT
            or settings.AGENCY_MEMBER_BASE_URL != MEMBER_URL
            or len(settings.SECRET_KEY) < 32
            or settings.SECRET_KEY == 'change-this-secret-key-in-production'):
        raise ValueError('Sandbox target configuration rejected; no connection attempted.')
    if settings.PADDLE_API_KEY and not settings.PADDLE_API_KEY.startswith('pdl_sdbx_apikey_'):
        raise ValueError('Only a Paddle sandbox API key is accepted.')
    if client_token and not client_token.startswith('test_'):
        raise ValueError('Only a sandbox client-side token is accepted.')
    if settings.AGENCY_STARTER_DELIVERY_ENABLED and not (
            settings.PADDLE_API_KEY and client_token
            and settings.PADDLE_WEBHOOK_SECRET
            and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL
            and settings.SMTP_USE_TLS and settings.SMTP_PORT == 587
            and (not settings.SMTP_USERNAME or settings.SMTP_PASSWORD)):
        raise ValueError('Sandbox credentials or TLS SMTP configuration incomplete.')


def create_app(*, test_engine=None, run_worker=True):
    client_token = os.environ.get('PADDLE_CLIENT_TOKEN', '')
    validate_configuration(client_token)
    engine = test_engine if test_engine is not None else create_engine(settings.DATABASE_URL)
    stop = threading.Event()
    webhook_lock = threading.Lock()

    def delivery_loop():
        while not stop.wait(3):
            try:
                with Session(engine) as db:
                    AgencyDeliveryService(db).run_batch(limit=1)
            except Exception:
                # Do not log provider responses, tokens, SMTP details or SQL parameters.
                print('Sandbox delivery iteration failed; inspect local status.', flush=True)

    @asynccontextmanager
    async def lifespan(application):
        for model in TABLES:
            model.__table__.create(engine, checkfirst=True)
        worker = None
        if run_worker and settings.AGENCY_STARTER_DELIVERY_ENABLED:
            worker = threading.Thread(target=delivery_loop, daemon=True)
            worker.start()
        try:
            yield
        finally:
            stop.set()
            if worker:
                worker.join(timeout=5)
            engine.dispose()

    application = FastAPI(lifespan=lifespan, docs_url=None,
                          redoc_url=None, openapi_url=None)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1'])

    def database():
        with Session(engine) as db:
            yield db

    application.dependency_overrides[db_session] = database
    # Reuse the real member handlers, but omit manual resend from this one-email test.
    application.include_router(member_router)
    application.router.routes = [route for route in application.router.routes
                                 if route.path != '/agency-member/request-access']

    @application.middleware('http')
    async def local_headers(request, call_next):
        origin = request.headers.get('origin')
        if origin and origin not in ('http://localhost:8097', 'http://127.0.0.1:8097'):
            return JSONResponse({'error': 'Origin rejected'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @application.get('/health')
    def health():
        with Session(engine) as db:
            rows = db.query(AgencyFulfilment).all()
            return {'environment': 'sandbox', 'armed': settings.AGENCY_STARTER_DELIVERY_ENABLED,
                    'orders': db.query(AgencyOrder).count(),
                    'delivery': [{'status': row.status, 'error': row.last_error} for row in rows]}

    @application.get('/checkout-config')
    def checkout_config():
        with Session(engine) as db:
            ready = settings.AGENCY_STARTER_DELIVERY_ENABLED and db.query(AgencyOrder).count() == 0
        return {'ready': ready, 'clientToken': client_token if ready else '',
                'priceId': PRICE, 'email': RECIPIENT}

    @application.get('/')
    def checkout_page():
        return FileResponse(HERE / 'checkout.html')

    @application.get('/member/')
    def member_page():
        return FileResponse(HERE / 'member.html')

    @application.post('/api/paddle/webhook')
    async def sandbox_webhook(request: Request):
        if not settings.AGENCY_STARTER_DELIVERY_ENABLED:
            raise HTTPException(503, 'Sandbox test is not armed.')
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > 1_048_576:
                raise HTTPException(413, 'Webhook too large.')
        with webhook_lock, Session(engine) as db:
            service = PaddleWebhookService(db)
            service._verify_signature(bytes(payload), request.headers.get('Paddle-Signature'))
            try:
                event = json.loads(payload)
            except (ValueError, UnicodeDecodeError):
                raise HTTPException(400, 'Invalid webhook JSON.') from None
            if not isinstance(event, dict):
                raise HTTPException(400, 'Invalid webhook object.')
            data = event.get('data')
            if (event.get('event_type') != 'transaction.completed'
                    or not isinstance(data, dict)
                    or not AgencyCommerceService(db).is_agency_transaction(data)):
                return {'received': True, 'handled': False}
            existing = db.query(AgencyOrder).first()
            if existing and existing.paddle_transaction_id != data.get('id'):
                return {'received': True, 'handled': False, 'reason': 'single_order_limit'}
            try:
                return service.handle_webhook_event(bytes(payload), request.headers.get('Paddle-Signature'))
            except HTTPException:
                raise
            except Exception:
                db.rollback()
                return JSONResponse({'error': 'Sandbox webhook processing failed.'}, status_code=500)

    return application
