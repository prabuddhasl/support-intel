import pytest
from jsonschema import ValidationError, validate

from services.common.schemas import (
    ENRICHED_EVENT_SCHEMA,
    ENRICHED_EVENT_SCHEMA_VERSION,
    TICKET_EVENT_SCHEMA,
    TICKET_EVENT_SCHEMA_VERSION,
)


def test_ticket_event_contract_valid():
    payload = {
        "schema_version": TICKET_EVENT_SCHEMA_VERSION,
        "event_id": "evt-12345678",
        "ticket_id": "T-1",
        "ts": "2026-01-28T00:00:00Z",
        "subject": "Login issue",
        "body": "Invalid password",
        "channel": "email",
        "priority": "high",
    }
    validate(instance=payload, schema=TICKET_EVENT_SCHEMA)


def test_ticket_event_contract_requires_schema_version():
    payload = {
        "event_id": "evt-12345678",
        "ticket_id": "T-1",
        "ts": "2026-01-28T00:00:00Z",
        "subject": "Login issue",
        "body": "Invalid password",
        "channel": "email",
        "priority": "high",
    }
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=TICKET_EVENT_SCHEMA)


def test_enriched_event_contract_valid():
    payload = {
        "schema_version": ENRICHED_EVENT_SCHEMA_VERSION,
        "event_id": "evt-12345678",
        "ticket_id": "T-1",
        "ts": "2026-01-28T00:00:00Z",
        "summary": "Payment issue",
        "category": "billing",
        "sentiment": "negative",
        "risk": 0.8,
        "suggested_reply": "We apologize for the issue.",
    }
    validate(instance=payload, schema=ENRICHED_EVENT_SCHEMA)


def test_enriched_event_contract_rejects_out_of_range_risk():
    payload = {
        "schema_version": ENRICHED_EVENT_SCHEMA_VERSION,
        "event_id": "evt-12345678",
        "ticket_id": "T-1",
        "ts": "2026-01-28T00:00:00Z",
        "summary": "Payment issue",
        "category": "billing",
        "sentiment": "negative",
        "risk": 1.5,
        "suggested_reply": "We apologize for the issue.",
    }
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=ENRICHED_EVENT_SCHEMA)
