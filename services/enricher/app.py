import json
from datetime import datetime, timezone

import psycopg
from jsonschema import validate, ValidationError
from confluent_kafka import Consumer, Producer
from anthropic import Anthropic

try:
    from services.enricher.config import (
        BOOTSTRAP,
        TOPIC_IN,
        TOPIC_OUT,
        TOPIC_DLQ,
        GROUP_ID,
        DATABASE_URL,
        MODEL,
    )
except Exception:  # pragma: no cover - fallback for direct script execution
    from config import (
        BOOTSTRAP,
        TOPIC_IN,
        TOPIC_OUT,
        TOPIC_DLQ,
        GROUP_ID,
        DATABASE_URL,
        MODEL,
    )

client = Anthropic()  # uses ANTHROPIC_API_KEY env var :contentReference[oaicite:1]{index=1}

try:
    from services.common.schemas import TICKET_EVENT_SCHEMA
except Exception:  # pragma: no cover - fallback for direct script execution
    from common.schemas import TICKET_EVENT_SCHEMA

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def dlq(producer: Producer, msg, err: str):
    payload = msg.value()
    try:
        payload_str = payload.decode("utf-8", errors="replace") if payload else None
    except Exception:
        payload_str = None

    rec = {
        "failed_topic": msg.topic(),
        "partition": msg.partition(),
        "offset": msg.offset(),
        "error": err,
        "payload": payload_str,
        "ts": now_iso(),
    }
    producer.produce(TOPIC_DLQ, value=json.dumps(rec).encode("utf-8"))
    producer.flush(5)

def already_processed(conn, event_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM processed_events WHERE event_id=%s", (event_id,)).fetchone()
    return row is not None

def mark_processed(conn, event_id: str):
    conn.execute("INSERT INTO processed_events(event_id) VALUES (%s) ON CONFLICT DO NOTHING", (event_id,))

def _mark_failed(conn, msg):
    """Best-effort: set status='failed' if the ticket_id can be extracted."""
    try:
        raw = msg.value()
        if raw:
            payload = json.loads(raw.decode("utf-8"))
            tid = payload.get("ticket_id")
            if tid:
                conn.execute(
                    "UPDATE enriched_tickets SET status='failed', updated_at=NOW() WHERE ticket_id=%s",
                    (tid,)
                )
                conn.commit()
    except Exception:
        conn.rollback()

def call_claude(ticket: dict) -> dict:
    # Keep it simple: force JSON output.
    system = (
        "You are a support operations assistant. "
        "Return ONLY valid JSON with keys: summary, category, sentiment, risk, suggested_reply. "
        "risk must be a number 0 to 1."
    )
    user = {
        "ticket_id": ticket["ticket_id"],
        "subject": ticket["subject"],
        "body": ticket["body"],
        "channel": ticket["channel"],
        "priority": ticket["priority"],
    }

    # Messages API usage follows Anthropic SDK pattern. :contentReference[oaicite:2]{index=2}
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user)}],
    )

    # SDK returns content blocks; take first text block.
    text = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text += block.text

    # Strip markdown code blocks if present
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]  # Remove ```
    if text.endswith("```"):
        text = text[:-3]  # Remove trailing ```
    text = text.strip()

    return json.loads(text)

def main():
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,  # we commit only after success/DLQ
    })
    producer = Producer({"bootstrap.servers": BOOTSTRAP})

    consumer.subscribe([TOPIC_IN])

    with psycopg.connect(DATABASE_URL) as conn:
        conn.autocommit = False

        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                # Kafka-level errors (not payload). Usually transient.
                print(f"[KAFKA] {msg.error()}")
                continue

            try:
                raw = msg.value()
                if not raw:
                    raise ValueError("empty payload")

                ticket = json.loads(raw.decode("utf-8"))
                validate(instance=ticket, schema=TICKET_EVENT_SCHEMA)

                event_id = ticket["event_id"]
                if already_processed(conn, event_id):
                    consumer.commit(message=msg, asynchronous=False)
                    continue

                enriched = call_claude(ticket)

                # basic sanity guard
                risk = float(enriched.get("risk", 0.0))
                if risk < 0.0 or risk > 1.0:
                    raise ValueError(f"risk out of range: {risk}")

                conn.execute(
                    """
                    INSERT INTO enriched_tickets(ticket_id, last_event_id, subject, body, channel, priority, customer_id, status, summary, category, sentiment, risk, suggested_reply, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'enriched',%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (ticket_id) DO UPDATE SET
                      last_event_id=EXCLUDED.last_event_id,
                      status='enriched',
                      summary=EXCLUDED.summary,
                      category=EXCLUDED.category,
                      sentiment=EXCLUDED.sentiment,
                      risk=EXCLUDED.risk,
                      suggested_reply=EXCLUDED.suggested_reply,
                      updated_at=NOW()
                    """,
                    (
                        ticket["ticket_id"],
                        event_id,
                        ticket.get("subject"),
                        ticket.get("body"),
                        ticket.get("channel"),
                        ticket.get("priority"),
                        ticket.get("customer_id"),
                        enriched.get("summary"),
                        enriched.get("category"),
                        enriched.get("sentiment"),
                        risk,
                        enriched.get("suggested_reply"),
                    )
                )
                mark_processed(conn, event_id)
                conn.commit()

                out = {
                    "event_id": event_id,
                    "ticket_id": ticket["ticket_id"],
                    "ts": now_iso(),
                    **enriched,
                }
                producer.produce(TOPIC_OUT, value=json.dumps(out).encode("utf-8"))
                producer.flush(5)

                consumer.commit(message=msg, asynchronous=False)
                print(f"[OK] ticket_id={ticket['ticket_id']} risk={risk:.2f}")

            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                conn.rollback()
                dlq(producer, msg, str(e))
                _mark_failed(conn, msg)
                consumer.commit(message=msg, asynchronous=False)
                print(f"[DLQ] {e} @ {msg.topic()}[{msg.partition()}] offset={msg.offset()}")

            except Exception as e:
                # transient-ish: rate limits etc. Anthropic returns 429 with retry-after header; in prod you honor it. :contentReference[oaicite:3]{index=3}
                conn.rollback()
                dlq(producer, msg, f"unexpected: {e}")
                _mark_failed(conn, msg)
                consumer.commit(message=msg, asynchronous=False)
                print(f"[DLQ] unexpected: {e}")

if __name__ == "__main__":
    main()
