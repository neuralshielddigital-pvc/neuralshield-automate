"""Synthetic session authorization gate tests; no real Whop calls."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.agency_saas_whop_authorization_gate import (
    PendingOwnershipAuthorization, redeem_ownership_authorization,
)
from app.services.agency_saas_whop_claim import (
    AuthenticatedSaasPrincipal, ProviderOwnershipProof,
)

NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)
SESSION = "session-synthetic-0123456789"
NONCE = "nonce-synthetic-0123456789"


class Store:
    def __init__(self):
        self.used = False
        self.calls = 0

    def consume_if_matches(self, **kwargs):
        self.calls += 1
        if self.used:
            return False
        self.used = True
        return True


class Verifier:
    def __init__(self, proof):
        self.proof = proof
        self.calls = 0

    def verify_authorization(self, **kwargs):
        self.calls += 1
        return self.proof


@pytest.fixture
def context():
    principal = AuthenticatedSaasPrincipal(
        str(uuid4()), str(uuid4()), True, True, True,
    )
    pending = PendingOwnershipAuthorization(
        NONCE, SESSION, principal.user_id, principal.tenant_id,
        NOW + timedelta(minutes=5),
    )
    proof = ProviderOwnershipProof(
        "sub_synthetic", "cus_synthetic",
        principal.user_id, principal.tenant_id, True, True,
    )
    return principal, pending, Verifier(proof), Store()


def redeem(context, **overrides):
    principal, pending, verifier, store = context
    args = dict(principal=principal, pending=pending, verifier=verifier,
                store=store, session_id=SESSION,
                authorization_response={"synthetic": True}, now=NOW)
    args.update(overrides)
    return redeem_ownership_authorization(**args)


def test_valid_proof_consumed_exactly_once(context):
    assert redeem(context).subscription_id == "sub_synthetic"
    with pytest.raises(ValueError, match="consumed"):
        redeem(context)
    assert context[3].calls == 2


@pytest.mark.parametrize("change", [
    {"session_id": "different-session-012345"},
    {"now": NOW + timedelta(minutes=6)},
    {"now": datetime(2026, 11, 22)},
])
def test_invalid_session_or_clock_fails_before_provider(context, change):
    with pytest.raises(ValueError):
        redeem(context, **change)
    assert context[2].calls == 0
    assert context[3].calls == 0


@pytest.mark.parametrize("change", [
    {"verified_by_provider": False},
    {"verified_for_session": False},
    {"authorized_user_id": "wrong"},
    {"authorized_tenant_id": "wrong"},
    {"subscription_id": ""},
    {"customer_id": ""},
])
def test_unverified_proof_never_consumes_nonce(context, change):
    context[2].proof = replace(context[2].proof, **change)
    with pytest.raises(ValueError, match="verification"):
        redeem(context)
    assert context[3].calls == 0


def test_wrong_principal_never_calls_provider(context):
    principal = replace(context[0], tenant_id=str(uuid4()))
    with pytest.raises(ValueError, match="session-bound"):
        redeem(context, principal=principal)
    assert context[2].calls == 0


def test_non_boolean_store_result_fails_closed(context):
    context[3].consume_if_matches = lambda **kwargs: 1
    with pytest.raises(ValueError, match="consumed"):
        redeem(context)


@pytest.mark.parametrize("field,value", [
    ("subscription_id", "   "),
    ("subscription_id", " sub_synthetic"),
    ("subscription_id", "sub_synthetic\n"),
    ("subscription_id", "sub\x00synthetic"),
    ("customer_id", "  "),
    ("customer_id", "cus_synthetic "),
    ("customer_id", "cus\tsynthetic"),
    ("customer_id", "cus\x7fsynthetic"),
])
def test_malformed_provider_identifiers_do_not_consume_nonce(context, field, value):
    context[2].proof = replace(context[2].proof, **{field: value})
    with pytest.raises(ValueError, match="verification"):
        redeem(context)
    assert context[3].calls == 0


@pytest.mark.parametrize("field,value", [
    ("subscription_id", "s" * 257),
    ("customer_id", "c" * 257),
])
def test_oversized_provider_identifiers_fail_before_nonce_consumption(context, field, value):
    context[2].proof = replace(context[2].proof, **{field: value})
    with pytest.raises(ValueError, match="verification"):
        redeem(context)
    assert context[3].calls == 0


@pytest.mark.parametrize("field,value", [
    ("nonce", "n" * 257),
    ("nonce", "nonce-synthetic-0123456789\\n"),
    ("nonce", " nonce-synthetic-0123456789"),
    ("session_id", "session-synthetic-0123456789\\t"),
    ("session_id", "session-synthetic-0123456789" + "x" * 257),
])
def test_malformed_pending_identifiers_fail_before_provider(context, field, value):
    pending = replace(context[1], **{field: value})
    with pytest.raises(ValueError, match="session-bound"):
        redeem(context, pending=pending)
    assert context[2].calls == 0
    assert context[3].calls == 0
