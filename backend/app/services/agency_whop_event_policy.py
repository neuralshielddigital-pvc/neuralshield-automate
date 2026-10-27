"""Pure fail-closed classification of Whop webhook event delivery.

This is intentionally *not* a provider event name allowlist. Production names
must be verified against Whop documentation and authenticated purchase lookup
before any fulfillment is wired. Unknown events are audit-only.
"""
from dataclasses import dataclass
from typing import Literal

from app.services.agency_whop_event_envelope import WhopEventEnvelope, provider_event_key


@dataclass(frozen=True)
class EventInboxDecision:
    event_key: str
    action: Literal["record_unhandled", "duplicate", "reject"]
    reason: str


def classify_whop_event_for_inbox(
    event: WhopEventEnvelope,
    *,
    existing_event_processed: bool | None,
) -> EventInboxDecision:
    key = provider_event_key(event)
    if not key.startswith("whop:") or len(key) > 260:
        return EventInboxDecision(key, "reject", "invalid_event_key")
    if existing_event_processed is True:
        return EventInboxDecision(key, "duplicate", "previously_processed")
    # The current integration is deliberately non-fulfilling. Once provider
    # verification is implemented this function can be extended with a
    # separately reviewed event allowlist.
    return EventInboxDecision(key, "record_unhandled", "not_activated")
