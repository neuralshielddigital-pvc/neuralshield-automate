"""Bounded, fail-closed Whop event envelope handling.

This parser does not authenticate a webhook: the caller MUST validate the
provider's current signature scheme before passing raw event bytes. It does
not trigger purchases, entitlements, or database writes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


MAX_EVENT_BYTES = 64 * 1024


@dataclass(frozen=True)
class WhopEventEnvelope:
    event_id: str
    event_type: str
    data: dict[str, Any]


def parse_authenticated_whop_event(
    payload: bytes,
    *,
    signature_verified: bool,
) -> WhopEventEnvelope:
    if not signature_verified:
        raise ValueError("Webhook signature has not been verified")
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_EVENT_BYTES:
        raise ValueError("Webhook payload is empty or oversized")
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid webhook JSON") from exc
    if not isinstance(message, dict):
        raise ValueError("Invalid event shape")
    event_id = message.get("id")
    event_type = message.get("type")
    data = message.get("data")
    if not isinstance(event_id, str) or not (1 <= len(event_id.strip()) <= 255):
        raise ValueError("Missing event identifier")
    if not isinstance(event_type, str) or not (1 <= len(event_type.strip()) <= 128):
        raise ValueError("Missing event type")
    if not isinstance(data, dict):
        raise ValueError("Invalid event data")
    return WhopEventEnvelope(
        event_id=event_id.strip(),
        event_type=event_type.strip(),
        data=data,
    )


def provider_event_key(event: WhopEventEnvelope) -> str:
    """Unique namespace for eventual durable webhook inbox."""
    return "whop:" + event.event_id
