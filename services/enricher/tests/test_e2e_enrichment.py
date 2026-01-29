import json
import os
import time
import uuid
from pathlib import Path
from urllib import request

import psycopg
import pytest


def _multipart_body(field_name: str, filename: str, content: bytes, boundary: str) -> bytes:
    headers = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        "Content-Type: text/markdown\r\n\r\n"
    )
    return headers.encode("utf-8") + content + b"\r\n"


def _post_multipart(url: str, field_name: str, filename: str, content: bytes) -> dict:
    boundary = f"----supportintel-{uuid.uuid4().hex}"
    body = _multipart_body(field_name, filename, content, boundary)
    body += f"--{boundary}--\r\n".encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


@pytest.mark.integration
def test_e2e_enrichment_includes_citations():
    if os.environ.get("RUN_E2E_TESTS") != "1":
        pytest.skip("Set RUN_E2E_TESTS=1 to run end-to-end enrichment test.")

    api_base = os.environ.get("API_BASE_URL", "http://localhost:8000")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set for end-to-end test.")
    if os.environ.get("STUB_LLM") != "1" and not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("Set ANTHROPIC_API_KEY or STUB_LLM=1 for end-to-end test.")

    kb_path = Path(__file__).resolve().parents[3] / "kb" / "sample_kb.md"
    if not kb_path.exists():
        pytest.skip("Sample KB file missing.")

    # Ensure KB is ingested.
    kb_url = f"{api_base}/kb/upload?source=sample_kb&source_url=https://example.com/kb"
    _post_multipart(kb_url, "file", kb_path.name, kb_path.read_bytes())

    ticket_payload = {
        "ticket_id": f"TICKET-{uuid.uuid4().hex[:8].upper()}",
        "subject": "Invalid password after reset",
        "body": "I reset my password twice but still get an invalid password error.",
        "channel": "email",
        "priority": "high",
        "customer_id": "CUST-1010",
    }
    created = _post_json(f"{api_base}/tickets", ticket_payload)
    ticket_id = created["ticket_id"]

    # Poll API until enriched or timeout.
    deadline = time.time() + 120
    ticket = {}
    while time.time() < deadline:
        ticket = _get_json(f"{api_base}/tickets/{ticket_id}")
        if ticket.get("status") == "enriched":
            break
        time.sleep(2)

    assert ticket.get("status") == "enriched"
    assert isinstance(ticket.get("citations"), list)
    assert ticket["citations"], "Expected non-empty citations list"

    db_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(db_url) as conn:
        row = conn.execute(
            "SELECT citations FROM enriched_tickets WHERE ticket_id=%s",
            (ticket_id,),
        ).fetchone()
    assert row is not None
    assert row[0] is not None
    assert isinstance(row[0], list)
