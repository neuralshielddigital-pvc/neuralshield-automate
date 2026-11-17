"""Read-only authenticated Whop membership transport.

This adapter intentionally does not implement WhopSubscriptionProvider: a Whop
membership is not equivalent to a verified paid SaaS subscription. In particular,
membership user_id must not be treated as an authorized local tenant identity,
and membership status alone cannot prove price, billing interval or payment.
No entitlement may be granted from this response.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirects(HTTPRedirectHandler):
    """Never forward a server-side Whop bearer token across HTTP redirects."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class WhopMembershipLookupError(RuntimeError):
    """Safe public error; never includes tokens or provider response bodies."""


@dataclass(frozen=True)
class WhopMembership:
    membership_id: str
    user_id: str
    variant_id: str | None
    status: str
    updated_at: datetime


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous provider JSON, including duplicate nested object keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate provider JSON field")
        result[key] = value
    return result


class WhopMembershipReader:
    """Official GET /api/v1/memberships/{id}, requiring member:basic:read.

    Supply a dedicated, server-side bearer token with minimum read scope.
    Do not log the token, response body, or buyer details.
    """

    def __init__(self, token: str, *, timeout_seconds: float = 5.0) -> None:
        if (not isinstance(token, str) or not token.strip() or token != token.strip()
                or any(ord(char) < 33 or ord(char) > 126 for char in token)):
            raise ValueError("Whop membership read credential is required")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 30:
            raise ValueError("Invalid Whop request timeout")
        self._token = token
        self._timeout = timeout_seconds

    def retrieve(self, membership_id: str) -> WhopMembership:
        if not isinstance(membership_id, str) or len(membership_id) > 128 or re.fullmatch(
            r"mem_[A-Za-z0-9]+", membership_id
        ) is None:
            raise ValueError("Invalid Whop membership identifier")
        request = Request(
            "https://api.whop.com/api/v1/memberships/" + membership_id,
            headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with build_opener(_NoRedirects()).open(request, timeout=self._timeout) as response:
                if response.status != 200:
                    raise WhopMembershipLookupError("Whop membership lookup failed")
                # Cap provider responses; never ingest unbounded remote JSON.
                payload = response.read(65537)
                if len(payload) > 65536:
                    raise WhopMembershipLookupError("Whop membership response too large")
            data = json.loads(payload, object_pairs_hook=_unique_json_object)
            if not isinstance(data, dict):
                raise ValueError("Invalid response object")
            if data.get("id") != membership_id:
                raise ValueError("Membership identity mismatch")
            user_id = data.get("user_id")
            status = data.get("status")
            updated_at = data.get("updated_at")
            variant_id = data.get("variant_id")
            if not isinstance(user_id, str) or len(user_id) > 128 or re.fullmatch(r"user_[A-Za-z0-9]+", user_id) is None:
                raise ValueError("Missing Whop buyer identity")
            if not isinstance(status, str) or not status.strip() or len(status) > 64 or status != status.strip():
                raise ValueError("Missing membership status")
            if variant_id is not None and (not isinstance(variant_id, str) or len(variant_id) > 128 or re.fullmatch(r"[A-Za-z0-9_]+", variant_id) is None):
                raise ValueError("Invalid membership variant")
            if not isinstance(updated_at, str):
                raise ValueError("Missing membership update time")
            observed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if observed.tzinfo is None or observed.utcoffset() is None:
                raise ValueError("Unaware membership timestamp")
            return WhopMembership(membership_id, user_id, variant_id, status, observed)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, UnicodeError, OverflowError, json.JSONDecodeError):
            raise WhopMembershipLookupError("Whop membership lookup or contract validation failed") from None
