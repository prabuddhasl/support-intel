import os
import uuid

import psycopg
import pytest


@pytest.mark.integration
def test_db_round_trip_for_enriched_tickets():
    if os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run integration tests.")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set for integration test.")

    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    ticket_id = f"IT-{uuid.uuid4().hex[:8]}"

    with psycopg.connect(database_url) as conn:
        conn.execute(
            "INSERT INTO enriched_tickets(ticket_id, status) VALUES (%s, %s)",
            (ticket_id, "pending"),
        )
        row = conn.execute(
            "SELECT ticket_id, status FROM enriched_tickets WHERE ticket_id=%s",
            (ticket_id,),
        ).fetchone()

    assert row == (ticket_id, "pending")
