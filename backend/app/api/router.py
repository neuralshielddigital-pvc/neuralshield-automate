from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.agency_admin import router as agency_admin_router
from app.api.routes.agency_member import router as agency_member_router
from app.api.routes.affiliate import router as affiliate_router
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.api_v1 import router as api_v1_router
from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.google_integrations import router as google_integrations_router
from app.api.routes.health import router as health_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.leads import router as leads_router
from app.api.routes.public import router as public_router
from app.api.routes.paddle import router as paddle_router
from app.api.routes.paddle_webhook import router as paddle_webhook_router
from app.api.routes.slack_integrations import router as slack_integrations_router
from app.api.routes.workflow_templates import router as workflow_templates_router
from app.api.routes.workflow_webhooks import router as workflow_webhooks_router
from app.api.routes.workflows import router as workflows_router


api_router = APIRouter()

api_router.include_router(admin_router)
api_router.include_router(agency_admin_router)
api_router.include_router(agency_member_router)
api_router.include_router(affiliate_router)
api_router.include_router(api_keys_router)
api_router.include_router(api_v1_router)
api_router.include_router(auth_router)
api_router.include_router(billing_router)
api_router.include_router(campaigns_router)
api_router.include_router(google_integrations_router)
api_router.include_router(health_router, tags=["health"])
api_router.include_router(integrations_router)
api_router.include_router(leads_router)
api_router.include_router(public_router)
api_router.include_router(paddle_router)
api_router.include_router(paddle_webhook_router)
api_router.include_router(slack_integrations_router)
api_router.include_router(workflow_templates_router)
api_router.include_router(workflow_webhooks_router)
api_router.include_router(workflows_router)
