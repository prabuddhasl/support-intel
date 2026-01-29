import importlib.util
import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from jsonschema import validate

# Avoid module name collision with services/api/app.py.
_app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
_spec = importlib.util.spec_from_file_location("enricher_app", _app_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

now_iso = _mod.now_iso
dlq = _mod.dlq
already_processed = _mod.already_processed
mark_processed = _mod.mark_processed
_mark_failed = _mod._mark_failed
call_claude = _mod.call_claude
_build_citations = _mod._build_citations
_merge_candidates = _mod._merge_candidates


# ── now_iso ──────────────────────────────────────────────────────────


def test_now_iso_returns_valid_utc_isoformat():
    result = now_iso()
    parsed = datetime.fromisoformat(result)
    assert parsed.tzinfo is not None
    assert parsed.tzinfo == UTC


def test_now_iso_is_current_time():
    before = datetime.now(UTC)
    result = datetime.fromisoformat(now_iso())
    after = datetime.now(UTC)
    assert before <= result <= after


# ── dlq ──────────────────────────────────────────────────────────────


def _make_mock_msg(
    value=b'{"ticket_id":"T-1"}',
    topic="support.tickets.v1",
    partition=0,
    offset=42,
):
    msg = MagicMock()
    msg.value.return_value = value
    msg.topic.return_value = topic
    msg.partition.return_value = partition
    msg.offset.return_value = offset
    return msg


def test_dlq_produces_to_dlq_topic():
    producer = MagicMock()
    msg = _make_mock_msg()

    dlq(producer, msg, "parse error")

    producer.produce.assert_called_once()
    call_args = producer.produce.call_args
    # First positional arg is the topic
    assert call_args[0][0] == "test.dlq"

    # Verify the DLQ record structure
    record = json.loads(call_args[1]["value"].decode("utf-8"))
    assert record["failed_topic"] == "support.tickets.v1"
    assert record["partition"] == 0
    assert record["offset"] == 42
    assert record["error"] == "parse error"
    assert record["payload"] == '{"ticket_id":"T-1"}'
    assert "ts" in record

    producer.flush.assert_called_once_with(5)


def test_dlq_handles_none_payload():
    producer = MagicMock()
    msg = _make_mock_msg(value=None)

    dlq(producer, msg, "empty")

    record = json.loads(producer.produce.call_args[1]["value"].decode("utf-8"))
    assert record["payload"] is None


def test_dlq_handles_non_utf8_payload():
    producer = MagicMock()
    msg = _make_mock_msg(value=b"\x80\x81\x82")

    dlq(producer, msg, "decode error")

    record = json.loads(producer.produce.call_args[1]["value"].decode("utf-8"))
    # Should use replacement characters, not crash
    assert record["payload"] is not None
    assert isinstance(record["payload"], str)


# ── already_processed ────────────────────────────────────────────────


def test_already_processed_returns_true_when_exists():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (1,)

    assert already_processed(conn, "evt-123") is True
    conn.execute.assert_called_once()
    assert "evt-123" in conn.execute.call_args[0][1]


def test_already_processed_returns_false_when_not_exists():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None

    assert already_processed(conn, "evt-999") is False


# ── mark_processed ───────────────────────────────────────────────────


def test_mark_processed_executes_insert():
    conn = MagicMock()

    mark_processed(conn, "evt-456")

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "INSERT INTO processed_events" in sql
    assert "ON CONFLICT DO NOTHING" in sql
    assert conn.execute.call_args[0][1] == ("evt-456",)


# ── _mark_failed ─────────────────────────────────────────────────────


def test_mark_failed_updates_ticket_status():
    conn = MagicMock()
    msg = _make_mock_msg(value=b'{"ticket_id":"T-100"}')

    _mark_failed(conn, msg)

    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    assert "UPDATE enriched_tickets SET status='failed'" in sql
    assert conn.execute.call_args[0][1] == ("T-100",)
    conn.commit.assert_called_once()


def test_mark_failed_swallows_exceptions():
    conn = MagicMock()
    msg = MagicMock()
    msg.value.side_effect = RuntimeError("boom")

    # Should not raise
    _mark_failed(conn, msg)
    conn.rollback.assert_called_once()


def test_mark_failed_skips_when_no_ticket_id():
    conn = MagicMock()
    msg = _make_mock_msg(value=b'{"event_id":"evt-1"}')

    _mark_failed(conn, msg)

    conn.execute.assert_not_called()


# ── _merge_candidates ────────────────────────────────────────────────


def test_merge_candidates_caps_secondary():
    primary = [{"id": 1}, {"id": 2}]
    secondary = [{"id": 3}, {"id": 4}, {"id": 5}]

    merged = _merge_candidates(primary, secondary, limit=10, secondary_max=1)

    assert merged == [{"id": 1}, {"id": 2}, {"id": 3}]


# ── call_claude ──────────────────────────────────────────────────────

SAMPLE_TICKET = {
    "ticket_id": "T-1",
    "subject": "Payment failed",
    "body": "Error code 5001",
    "channel": "email",
    "priority": "high",
}


def _mock_claude_response(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


@patch.object(_mod, "client")
def test_call_claude_parses_clean_json(mock_client):
    response_json = json.dumps(
        {
            "summary": "Payment issue",
            "category": "billing",
            "sentiment": "negative",
            "risk": 0.8,
            "suggested_reply": "We apologize for the issue.",
        }
    )
    mock_client.messages.create.return_value = _mock_claude_response(response_json)

    result = call_claude(SAMPLE_TICKET)

    assert result["summary"] == "Payment issue"
    assert result["category"] == "billing"
    assert result["sentiment"] == "negative"
    assert result["risk"] == 0.8
    assert result["suggested_reply"] == "We apologize for the issue."

    # Verify API was called correctly
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["max_tokens"] == 400
    assert len(call_kwargs["messages"]) == 1


def test_enriched_event_schema_contract():
    event = {
        "schema_version": _mod.ENRICHED_EVENT_SCHEMA_VERSION,
        "event_id": "evt-12345678",
        "ticket_id": "T-1",
        "ts": datetime.now(UTC).isoformat(),
        "summary": "Payment issue",
        "category": "billing",
        "sentiment": "negative",
        "risk": 0.8,
        "suggested_reply": "We apologize for the issue.",
        "citations": [
            {"chunk_id": 12, "title": "Billing FAQ", "heading_path": "Payments"},
        ],
    }

    validate(instance=event, schema=_mod.ENRICHED_EVENT_SCHEMA)


def test_build_citations_defaults_missing_fields():
    chunks = [
        {"id": 1, "title": "Doc A", "heading_path": "Intro"},
        {"id": 2, "title": None, "heading_path": None},
        {"title": "No ID"},
    ]

    citations = _build_citations(chunks)

    assert citations == [
        {"chunk_id": 1, "title": "Doc A", "heading_path": "Intro"},
        {"chunk_id": 2, "title": "Untitled", "heading_path": ""},
    ]


@patch.object(_mod, "client")
def test_call_claude_strips_json_markdown_fences(mock_client):
    raw = (
        '```json\n{"summary":"s","category":"c","sentiment":"n","risk":0.5,'
        '"suggested_reply":"r"}\n```'
    )
    mock_client.messages.create.return_value = _mock_claude_response(raw)

    result = call_claude(SAMPLE_TICKET)
    assert result["summary"] == "s"
    assert result["risk"] == 0.5


@patch.object(_mod, "client")
def test_call_claude_strips_plain_markdown_fences(mock_client):
    raw = (
        '```\n{"summary":"s","category":"c","sentiment":"n","risk":0.1,'
        '"suggested_reply":"r"}\n```'
    )
    mock_client.messages.create.return_value = _mock_claude_response(raw)

    result = call_claude(SAMPLE_TICKET)
    assert result["risk"] == 0.1


@patch.object(_mod, "client")
def test_call_claude_includes_kb_context(mock_client):
    response_json = json.dumps(
        {
            "summary": "Payment issue",
            "category": "billing",
            "sentiment": "negative",
            "risk": 0.8,
            "suggested_reply": "We apologize for the issue.",
        }
    )
    mock_client.messages.create.return_value = _mock_claude_response(response_json)

    call_claude(SAMPLE_TICKET, kb_context="KB Context: example")

    system = mock_client.messages.create.call_args[1]["system"]
    assert "KB Context: example" in system


@patch.object(_mod, "client")
def test_call_claude_raises_on_invalid_json(mock_client):
    mock_client.messages.create.return_value = _mock_claude_response("This is not JSON")

    try:
        call_claude(SAMPLE_TICKET)
        assert False, "Should have raised json.JSONDecodeError"
    except json.JSONDecodeError:
        pass
