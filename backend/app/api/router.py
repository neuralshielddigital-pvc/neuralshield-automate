from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.affiliate import router as affiliate_router
from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.api.routes.public import router as public_router
from app.api.routes.stripe_webhook import router as stripe_webhook_router
from app.api.routes.workflow_webhooks import router as workflow_webhooks_router
from app.api.routes.workflows import router as workflows_router


api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(affiliate_router)
api_router.include_router(auth_router)
api_router.include_router(billing_router)
api_router.include_router(campaigns_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(leads_router)
api_router.include_router(public_router)
api_router.include_router(stripe_webhook_router)
api_router.include_router(workflow_webhooks_router)
api_router.include_router(workflows_router)
