"""Session-owned checkout intent contract for Automation SaaS only."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hmac


class CommercialError(ValueError):
    pass


class ProvisioningState(str, Enum):
    PENDING_PAYMENT = "pending_payment"


@dataclass(frozen=True)
class Plan:
    catalog_version: str
    code: str
    currency: str
    interval: str
    amount_minor: int
    entitlement_profile: str


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_id: str
    authenticated: bool = True

    def require(self) -> None:
        if not self.authenticated or not self.tenant_id or not self.actor_id:
            raise CommercialError("authentication_required")


@dataclass
class CheckoutIntent:
    id: str
    tenant_id: str
    plan: Plan
    idempotency_key: str
    state: ProvisioningState = ProvisioningState.PENDING_PAYMENT
    payment_id: str | None = None


def require_owner(ctx: TenantContext, tenant_id: str) -> None:
    ctx.require()
    if not hmac.compare_digest(ctx.tenant_id, tenant_id):
        raise CommercialError("tenant_mismatch")
