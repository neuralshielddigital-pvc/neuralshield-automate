import json
import pytest

from app.services.agency_whop_event_envelope import (
    MAX_EVENT_BYTES, parse_authenticated_whop_event, provider_event_key,
)

EVENT = {"id": "synthetic_evt_1", "type": "synthetic.purchase", "data": {"order": "test"}}


def test_signed_bounded_event_parses_into_provider_namespace():
    event = parse_authenticated_whop_event(
        json.dumps(EVENT).encode(), signature_verified=True,
    )
    assert event.event_id == "synthetic_evt_1"
    assert provider_event_key(event) == "whop:synthetic_evt_1"


def test_unsigned_event_never_enters_processing():
    with pytest.raises(ValueError, match="signature"):
        parse_authenticated_whop_event(json.dumps(EVENT).encode(), signature_verified=False)


@pytest.mark.parametrize("payload", [
    b"", b"not-json", b"[]", b"{}", b"x" * (MAX_EVENT_BYTES + 1),
    json.dumps({"id": "", "type": "synthetic.purchase", "data": {}}).encode(),
    json.dumps({"id": "a", "type": "", "data": {}}).encode(),
    json.dumps({"id": "a", "type": "b", "data": []}).encode(),
])
def test_malformed_event_is_rejected(payload):
    with pytest.raises(ValueError):
        parse_authenticated_whop_event(payload, signature_verified=True)
