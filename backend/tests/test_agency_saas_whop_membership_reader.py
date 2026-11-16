"""No-network contract tests for authenticated Whop membership retrieval."""
import io
import json
from unittest.mock import patch

import pytest

from app.services.agency_saas_whop_membership_reader import (
    WhopMembershipLookupError, WhopMembershipReader,
)


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.payload[:limit]


def payload(**overrides):
    data = {
        "id": "mem_123ABC",
        "user_id": "user_abc123",
        "variant_id": "var_123",
        "status": "active",
        "updated_at": "2026-11-16T00:00:00Z",
    }
    data.update(overrides)
    return json.dumps(data).encode()


def test_authenticated_get_uses_fixed_whop_host_and_bounded_timeout():
    def fetch(request, timeout):
        assert request.full_url == "https://api.whop.com/api/v1/memberships/mem_123ABC"
        assert request.get_header("Authorization") == "Bearer test-secret"
        assert timeout == 5.0
        return Response(payload())

    with patch("app.services.agency_saas_whop_membership_reader.urlopen", fetch):
        membership = WhopMembershipReader("test-secret").retrieve("mem_123ABC")
    assert membership.user_id == "user_abc123"
    assert membership.updated_at.utcoffset().total_seconds() == 0


@pytest.mark.parametrize("identifier", ["../payments", "mem_abc/def", "sub_123", "", "mem_%2f"])
def test_rejects_untrusted_lookup_paths_before_network(identifier):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen") as fetch:
        with pytest.raises(ValueError):
            WhopMembershipReader("test-secret").retrieve(identifier)
        fetch.assert_not_called()


@pytest.mark.parametrize("change", [
    {"id": "mem_other"},
    {"user_id": None},
    {"updated_at": "2026-11-16T00:00:00"},
    {"variant_id": []},
])
def test_invalid_contract_never_returns_verified_membership(change):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(payload(**change))):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")


def test_rejects_oversized_response():
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(b"x" * 65537)):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")
