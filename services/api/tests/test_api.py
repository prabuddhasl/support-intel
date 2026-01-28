import json
import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.api import app


def _make_conn():
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = None
    return conn


@pytest.fixture()
def client():
    return TestClient(app.app)


def test_root_returns_endpoints(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "Support Intel API"
    assert "health" in body["endpoints"]
    assert "create_ticket" in body["endpoints"]


def test_health_check_healthy(client, monkeypatch):
    conn = _make_conn()
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["database"] == "healthy"
    assert "timestamp" in body


def test_health_check_degraded_when_db_fails(client, monkeypatch):
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(app, "get_db_connection", _boom)

    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["database"].startswith("unhealthy:")


def test_validation_error_format(client):
    resp = client.post("/tickets", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert isinstance(body["error"]["details"], list)


def test_create_ticket_publishes_to_kafka_and_db(client, monkeypatch):
    conn = _make_conn()
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)
    producer = MagicMock()
    monkeypatch.setattr(app, "producer", producer)

    fixed_uuid = "1234567890abcdef1234567890abcdef"
    monkeypatch.setattr(app.uuid, "uuid4", lambda: type("U", (), {"hex": fixed_uuid})())

    payload = {
        "subject": "Cannot login",
        "body": "Auth error",
        "channel": "email",
        "priority": "high",
        "customer_id": "CUST-1",
    }

    resp = client.post("/tickets", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["event_id"].startswith("evt-")
    assert body["ticket_id"].startswith("TICKET-")

    conn.execute.assert_called_once()
    producer.produce.assert_called_once()
    assert producer.produce.call_args[0][0] == app.TOPIC_IN

    produced = json.loads(producer.produce.call_args[1]["value"].decode("utf-8"))
    assert produced["schema_version"] == app.TICKET_EVENT_SCHEMA_VERSION
    assert produced["customer_id"] == "CUST-1"
    assert produced["subject"] == payload["subject"]


def test_create_ticket_handles_failure(client, monkeypatch):
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(app, "get_db_connection", _boom)

    resp = client.post(
        "/tickets",
        json={
            "subject": "s",
            "body": "b",
            "channel": "email",
            "priority": "low",
        },
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "http_500"
    assert "Failed to create ticket" in body["error"]["message"]


def test_list_tickets_filters_and_pagination(client, monkeypatch):
    conn = _make_conn()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (2,)
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        (
            "T-1",
            "evt-1",
            "subj",
            "body",
            "email",
            "high",
            "C-1",
            "enriched",
            "sum",
            "billing",
            "negative",
            0.8,
            "reply",
            datetime.now(UTC),
            datetime.now(UTC),
        ),
        (
            "T-2",
            "evt-2",
            "subj2",
            "body2",
            "chat",
            "low",
            None,
            "pending",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    ]
    conn.execute.side_effect = [count_cursor, rows_cursor]
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    query = "/tickets?risk_min=0.5&category=billing&page=1&page_size=2&sort_by=risk&sort_order=asc"
    resp = client.get(query)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["tickets"]) == 2
    assert body["tickets"][0]["ticket_id"] == "T-1"


def test_list_tickets_invalid_sort_defaults(client, monkeypatch):
    conn = _make_conn()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (0,)
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = []
    conn.execute.side_effect = [count_cursor, rows_cursor]
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/tickets?sort_by=bad&sort_order=bad")
    assert resp.status_code == 200
    query = conn.execute.call_args_list[1][0][0]
    assert "ORDER BY updated_at desc" in query


def test_get_ticket_found(client, monkeypatch):
    conn = _make_conn()
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        "T-1",
        "evt-1",
        "subj",
        "body",
        "email",
        "high",
        "C-1",
        "enriched",
        "sum",
        "billing",
        "negative",
        0.8,
        "reply",
        datetime.now(UTC),
        datetime.now(UTC),
    )
    conn.execute.return_value = cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/tickets/T-1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticket_id"] == "T-1"
    assert body["risk"] == 0.8


def test_get_ticket_not_found(client, monkeypatch):
    conn = _make_conn()
    cursor = MagicMock()
    cursor.fetchone.return_value = None
    conn.execute.return_value = cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/tickets/NOPE")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "http_404"
    assert "not found" in body["error"]["message"].lower()


def test_analytics_summary(client, monkeypatch):
    conn = _make_conn()
    summary_cursor = MagicMock()
    summary_cursor.fetchone.return_value = (10, 0.52345, 3)
    category_cursor = MagicMock()
    category_cursor.fetchall.return_value = [("billing", 4), ("account", 2)]
    sentiment_cursor = MagicMock()
    sentiment_cursor.fetchall.return_value = [("negative", 5)]
    conn.execute.side_effect = [summary_cursor, category_cursor, sentiment_cursor]
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tickets"] == 10
    assert body["avg_risk"] == 0.523
    assert body["high_risk_count"] == 3
    assert body["by_category"]["billing"] == 4
    assert body["by_sentiment"]["negative"] == 5


def test_get_categories(client, monkeypatch):
    conn = _make_conn()
    cursor = MagicMock()
    cursor.fetchall.return_value = [("billing",), ("account",)]
    conn.execute.return_value = cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/categories")
    assert resp.status_code == 200
    assert resp.json() == ["billing", "account"]


def test_get_sentiments(client, monkeypatch):
    conn = _make_conn()
    cursor = MagicMock()
    cursor.fetchall.return_value = [("negative",), ("positive",)]
    conn.execute.return_value = cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/sentiments")
    assert resp.status_code == 200
    assert resp.json() == ["negative", "positive"]


def test_kb_chunk_text_heading_paragraph():
    text = """# Title

## Section A
Paragraph one.

Paragraph two.
"""
    chunks = app._chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) == 2
    assert chunks[0]["content"].startswith("# Title")
    assert "## Section A" in chunks[1]["content"]
    assert "Paragraph one." in chunks[1]["content"]
    assert chunks[1]["heading_path"].endswith("Section A")


def test_kb_upload_ingests_txt(client, monkeypatch):
    if getattr(sys.modules.get("python_multipart"), "__fake__", False):
        pytest.skip("python-multipart not installed in test environment")

    conn = _make_conn()

    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = None
    insert_cursor = MagicMock()
    insert_cursor.fetchone.return_value = (1,)

    def _execute_side_effect(*args, **kwargs):
        if "SELECT id FROM kb_documents" in args[0]:
            return select_cursor
        if "INSERT INTO kb_documents" in args[0]:
            return insert_cursor
        return None

    conn.execute.side_effect = _execute_side_effect
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    payload = b"""# Title

## Section A
Paragraph one.
"""
    resp = client.post(
        "/kb/upload?source=unit-test&source_url=https://example.com/kb",
        files={"file": ("sample.txt", payload, "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ingested"
    assert body["doc_id"] == 1
    assert body["chunks"] >= 1


def test_kb_upload_deduplicates_by_sha(client, monkeypatch):
    if getattr(sys.modules.get("python_multipart"), "__fake__", False):
        pytest.skip("python-multipart not installed in test environment")

    conn = _make_conn()
    select_cursor = MagicMock()
    select_cursor.fetchone.return_value = (42,)
    conn.execute.return_value = select_cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    payload = b"""# Title

## Section A
Paragraph one.
"""
    resp = client.post(
        "/kb/upload?source_url=https://example.com/kb",
        files={"file": ("sample.txt", payload, "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "already_ingested"
    assert body["doc_id"] == 42


def test_kb_search(client, monkeypatch):
    conn = _make_conn()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (10, 1, 0, "Refund policy: 14 days", "sample_kb.md", "help_center"),
        (11, 1, 1, "Refunds within 14 days", "sample_kb.md", "help_center"),
    ]
    conn.execute.return_value = cursor
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/kb/search?q=refund&limit=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "refund"
    assert body["count"] == 2
    assert body["results"][0]["filename"] == "sample_kb.md"


def test_kb_upload_rejects_large_file(client, monkeypatch):
    if getattr(sys.modules.get("python_multipart"), "__fake__", False):
        pytest.skip("python-multipart not installed in test environment")

    monkeypatch.setattr(app, "MAX_UPLOAD_BYTES", 10)
    payload = b"x" * 20
    resp = client.post(
        "/kb/upload",
        files={"file": ("sample.txt", payload, "text/plain")},
    )
    assert resp.status_code == 413


def test_kb_upload_rejects_bad_content_type(client):
    if getattr(sys.modules.get("python_multipart"), "__fake__", False):
        pytest.skip("python-multipart not installed in test environment")

    payload = b"hello"
    resp = client.post(
        "/kb/upload",
        files={"file": ("sample.txt", payload, "application/pdf")},
    )
    assert resp.status_code == 400
