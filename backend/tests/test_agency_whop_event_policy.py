from app.services.agency_whop_event_envelope import WhopEventEnvelope
from app.services.agency_whop_event_policy import classify_whop_event_for_inbox


def test_unknown_whop_events_never_auto_grant():
    event = WhopEventEnvelope("event_001", "unknown.purchase", {"status": "paid"})
    result = classify_whop_event_for_inbox(event, existing_event_processed=None)
    assert result.action == "record_unhandled"
    assert result.event_key == "whop:event_001"


def test_duplicate_event_is_idempotent():
    event = WhopEventEnvelope("event_001", "unknown.purchase", {})
    result = classify_whop_event_for_inbox(event, existing_event_processed=True)
    assert result.action == "duplicate"


def test_incomplete_prior_event_does_not_trigger_grant():
    event = WhopEventEnvelope("event_001", "unknown.purchase", {})
    result = classify_whop_event_for_inbox(event, existing_event_processed=False)
    assert result.action == "record_unhandled"
