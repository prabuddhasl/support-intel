import json
from datetime import datetime, timezone
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
    assert produced["customer_id"] == "CUST-1"
    assert produced["subject"] == payload["subject"]


def test_create_ticket_handles_failure(client, monkeypatch):
    def _boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(app, "get_db_connection", _boom)

    resp = client.post("/tickets", json={
        "subject": "s",
        "body": "b",
        "channel": "email",
        "priority": "low",
    })
    assert resp.status_code == 500
    assert "Failed to create ticket" in resp.text


def test_list_tickets_filters_and_pagination(client, monkeypatch):
    conn = _make_conn()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (2,)
    rows_cursor = MagicMock()
    rows_cursor.fetchall.return_value = [
        ("T-1", "evt-1", "subj", "body", "email", "high", "C-1", "enriched",
         "sum", "billing", "negative", 0.8, "reply", datetime.now(timezone.utc), datetime.now(timezone.utc)),
        ("T-2", "evt-2", "subj2", "body2", "chat", "low", None, "pending",
         None, None, None, None, None, None, None),
    ]
    conn.execute.side_effect = [count_cursor, rows_cursor]
    monkeypatch.setattr(app, "get_db_connection", lambda: conn)

    resp = client.get("/tickets?risk_min=0.5&category=billing&page=1&page_size=2&sort_by=risk&sort_order=asc")
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
        "T-1", "evt-1", "subj", "body", "email", "high", "C-1", "enriched",
        "sum", "billing", "negative", 0.8, "reply",
        datetime.now(timezone.utc), datetime.now(timezone.utc)
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
    assert "not found" in resp.text.lower()


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
