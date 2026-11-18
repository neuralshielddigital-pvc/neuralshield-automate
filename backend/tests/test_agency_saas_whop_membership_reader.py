"""No-network contract tests for authenticated Whop membership retrieval."""
import json
import math
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


@pytest.mark.parametrize("identifier", ["../payments", "mem_abc/def", "sub_123", "", "mem_%2f", "mem_" + "A" * 125, "mem_" + "A" * 5000])
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


@pytest.mark.parametrize("raw_response", [
    b"\\xff\\xfe\\xfa",  # invalid UTF-8 JSON payload
    b'{"id":"mem_123ABC","user_id":"user_abc123","status":"active","updated_at":"999999999999-01-01T00:00:00Z"}',
])
def test_malformed_encoding_or_out_of_range_timestamp_fails_closed(raw_response):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(raw_response)):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")


@pytest.mark.parametrize("token", ["", " token", "token ", "token\nInjected: value", "token\r", "token\t", "tökén"])
def test_rejects_unsafe_bearer_tokens_before_network(token):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen") as fetch:
        with pytest.raises(ValueError):
            WhopMembershipReader(token)
        fetch.assert_not_called()


@pytest.mark.parametrize("timeout", [0, -1, 31, True, "5", math.nan, math.inf, -math.inf])
def test_rejects_invalid_timeout_configuration(timeout):
    with pytest.raises(ValueError):
        WhopMembershipReader("test-secret", timeout_seconds=timeout)


@pytest.mark.parametrize("change", [
    {"user_id": "user_abc/other"},
    {"user_id": "user_" + "A" * 200},
    {"status": " active "},
    {"status": "x" * 200},
    {"variant_id": "var_123/other"},
    {"variant_id": "v" * 200},
])
def test_untrusted_membership_fields_are_bounded_and_not_usable_for_identity(change):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(payload(**change))):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")


@pytest.mark.parametrize("raw_response", [
    b'{"id":"mem_123ABC","id":"mem_other","user_id":"user_abc123","status":"active","updated_at":"2026-11-16T00:00:00Z"}',
    b'{"id":"mem_123ABC","user_id":"user_abc123","status":"active","updated_at":"2026-11-16T00:00:00Z","metadata":{"owner":"a","owner":"b"}}',
])
def test_duplicate_provider_json_keys_fail_closed(raw_response):
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(raw_response)):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")


def test_membership_transport_disables_redirects_to_protect_bearer_token():
    from urllib.request import Request
    from app.services.agency_saas_whop_membership_reader import _NoRedirects, urlopen

    handler = _NoRedirects()
    request = Request(
        "https://api.whop.com/api/v1/memberships/mem_123ABC",
        headers={"Authorization": "Bearer secret"},
    )
    assert handler.redirect_request(
        request, None, 302, "Found", {}, "https://attacker.example/collect"
    ) is None

    class FakeOpener:
        def open(self, req, *, timeout):
            assert req is request
            assert timeout == 3
            return Response(payload())

    with patch(
        "app.services.agency_saas_whop_membership_reader.build_opener",
        return_value=FakeOpener(),
    ) as factory:
        with urlopen(request, timeout=3) as response:
            assert response.status == 200
        assert isinstance(factory.call_args.args[0], _NoRedirects)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_provider_json_constants_fail_closed(constant):
    raw = payload().decode().replace('"status": "active"', '"status": "active", "unexpected": ' + constant)
    with patch("app.services.agency_saas_whop_membership_reader.urlopen", return_value=Response(raw.encode())):
        with pytest.raises(WhopMembershipLookupError):
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")


def test_interrupted_provider_response_never_leaks_partial_payload():
    from http.client import IncompleteRead

    class InterruptedResponse(Response):
        def read(self, limit):
            raise IncompleteRead(b"secret-provider-body", 10)

    with patch(
        "app.services.agency_saas_whop_membership_reader.urlopen",
        return_value=InterruptedResponse(b""),
    ):
        with pytest.raises(WhopMembershipLookupError) as error:
            WhopMembershipReader("test-secret").retrieve("mem_123ABC")
    assert "secret-provider-body" not in str(error.value)
    assert error.value.__cause__ is None
