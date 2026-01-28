import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import psycopg
from anthropic import Anthropic
from confluent_kafka import Consumer, Producer
from jsonschema import ValidationError, validate

if TYPE_CHECKING:
    from services.enricher.config import (
        BOOTSTRAP,
        DATABASE_URL,
        EMBEDDING_MODEL,
        GROUP_ID,
        KB_CANDIDATES,
        KB_TOP_K,
        MODEL,
        RERANK_ENABLED,
        RERANK_MODEL,
        TOPIC_DLQ,
        TOPIC_IN,
        TOPIC_OUT,
    )
else:
    try:
        from services.enricher.config import (
            BOOTSTRAP,
            DATABASE_URL,
            EMBEDDING_MODEL,
            GROUP_ID,
            KB_CANDIDATES,
            KB_TOP_K,
            MODEL,
            RERANK_ENABLED,
            RERANK_MODEL,
            TOPIC_DLQ,
            TOPIC_IN,
            TOPIC_OUT,
        )
    except Exception:  # pragma: no cover - fallback for direct script execution
        from config import (
            BOOTSTRAP,
            DATABASE_URL,
            EMBEDDING_MODEL,
            GROUP_ID,
            KB_CANDIDATES,
            KB_TOP_K,
            MODEL,
            RERANK_ENABLED,
            RERANK_MODEL,
            TOPIC_DLQ,
            TOPIC_IN,
            TOPIC_OUT,
        )

from services.common.embeddings import embed_text
from services.common.reranker import rerank_chunks
from services.common.vector_store import search_similar_chunks

client = Anthropic()  # uses ANTHROPIC_API_KEY env var :contentReference[oaicite:1]{index=1}

if TYPE_CHECKING:
    from services.common.schemas import (
        CATEGORY_ENUM,
        ENRICHED_EVENT_SCHEMA,
        ENRICHED_EVENT_SCHEMA_VERSION,
        SENTIMENT_ENUM,
        TICKET_EVENT_SCHEMA,
    )
else:
    try:
        from services.common.schemas import (
            CATEGORY_ENUM,
            ENRICHED_EVENT_SCHEMA,
            ENRICHED_EVENT_SCHEMA_VERSION,
            SENTIMENT_ENUM,
            TICKET_EVENT_SCHEMA,
        )
    except Exception:  # pragma: no cover - fallback for direct script execution
        from common.schemas import (
            CATEGORY_ENUM,
            ENRICHED_EVENT_SCHEMA,
            ENRICHED_EVENT_SCHEMA_VERSION,
            SENTIMENT_ENUM,
            TICKET_EVENT_SCHEMA,
        )


def now_iso():
    return datetime.now(UTC).isoformat()


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
    conn.execute(
        "INSERT INTO processed_events(event_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (event_id,),
    )


def _mark_failed(conn, msg):
    """Best-effort: set status='failed' if the ticket_id can be extracted."""
    try:
        raw = msg.value()
        if raw:
            payload = json.loads(raw.decode("utf-8"))
            tid = payload.get("ticket_id")
            if tid:
                conn.execute(
                    "UPDATE enriched_tickets SET status='failed', updated_at=NOW()"
                    " WHERE ticket_id=%s",
                    (tid,),
                )
                conn.commit()
    except Exception:
        conn.rollback()


def _format_kb_context(chunks: list[dict], max_chars: int = 4000) -> str:
    if not chunks:
        return ""
    parts: list[str] = []
    total = 0
    for chunk in chunks:
        header = f"{chunk.get('title') or 'Untitled'} | {chunk.get('heading_path') or ''}".strip()
        content = (chunk.get("content") or "").strip()
        block = f"{header}\n{content}".strip()
        if not block:
            continue
        if total + len(block) + 2 > max_chars:
            remaining = max_chars - total
            if remaining > 0:
                parts.append(block[:remaining])
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n".join(parts)


def call_claude(ticket: dict, kb_context: str | None = None) -> dict:
    # Keep it simple: force JSON output.
    system = (
        "You are a support operations assistant. "
        "Use ONLY the KB Context when proposing troubleshooting steps or policy statements. "
        "If the KB Context does not cover the issue, ask 1–2 clarifying questions and "
        "avoid guessing. "
        f"Allowed categories: {', '.join(CATEGORY_ENUM)}. "
        f"Allowed sentiments: {', '.join(SENTIMENT_ENUM)}. "
        "Return ONLY valid JSON with keys: summary, category, sentiment, risk, suggested_reply. "
        "risk must be a number 0 to 1. "
        "Suggested reply format: 1 short acknowledgment, then 2–4 bullet steps, then "
        "next-step ask. "
        "Keep suggested_reply under 140 words."
    )
    if kb_context:
        system = f"{system}\n\nKB Context:\n{kb_context}"
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
            text_block = getattr(block, "text", None)
            if isinstance(text_block, str):
                text += text_block

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


def _clamp_risk(value) -> float:
    try:
        risk = float(value)
    except Exception:
        return 0.0
    if risk < 0.0:
        return 0.0
    if risk > 1.0:
        return 1.0
    return risk


def _normalize_sentiment(value: str | None) -> str:
    if not value:
        return "neutral"
    v = value.strip().lower()
    if v in SENTIMENT_ENUM:
        return v
    if v in {"frustrated", "angry", "upset", "negative"}:
        return "negative"
    if v in {"happy", "satisfied", "positive"}:
        return "positive"
    return "neutral"


def _normalize_category(value: str | None) -> str:
    if not value:
        return "general"
    v = value.strip().lower()
    if v in CATEGORY_ENUM:
        return v
    if "billing" in v or "invoice" in v or "refund" in v or "charge" in v:
        return "billing"
    if "security" in v or "breach" in v or "incident" in v:
        return "security_incident"
    if "refresh" in v or "data" in v and "refresh" in v:
        return "data_refresh"
    if "export" in v:
        return "exports"
    if "feature" in v or "roadmap" in v:
        return "feature_request"
    if "oauth" in v or "api key" in v or "integration" in v:
        return "integration"
    if "alert" in v or "notification" in v or "slack" in v:
        return "notifications"
    if "login" in v or "password" in v or "account" in v or "access" in v:
        return "account_access"
    return "general"


def _trim_reply(text: str | None, max_words: int = 140) -> str:
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip() + "…"


def main():
    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # we commit only after success/DLQ
        }
    )
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

                query_text = f"{ticket.get('subject', '')}\n\n{ticket.get('body', '')}".strip()
                query_embedding = embed_text(query_text, model_name=EMBEDDING_MODEL)
                candidates = search_similar_chunks(conn, query_embedding, top_k=KB_CANDIDATES)
                if RERANK_ENABLED:
                    chunks = rerank_chunks(query_text, candidates, RERANK_MODEL, KB_TOP_K)
                else:
                    chunks = candidates[:KB_TOP_K]
                kb_context = _format_kb_context(chunks)

                enriched = call_claude(ticket, kb_context=kb_context)

                # Normalize and validate enrichment
                enriched["category"] = _normalize_category(enriched.get("category"))
                enriched["sentiment"] = _normalize_sentiment(enriched.get("sentiment"))
                enriched["risk"] = _clamp_risk(enriched.get("risk", 0.0))
                enriched["suggested_reply"] = _trim_reply(enriched.get("suggested_reply"))

                risk = enriched["risk"]

                conn.execute(
                    """
                    INSERT INTO enriched_tickets(
                      ticket_id, last_event_id, subject, body, channel, priority, customer_id,
                      status, summary, category, sentiment, risk, suggested_reply, updated_at
                    )
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
                    ),
                )
                mark_processed(conn, event_id)
                conn.commit()

                out = {
                    "schema_version": ENRICHED_EVENT_SCHEMA_VERSION,
                    "event_id": event_id,
                    "ticket_id": ticket["ticket_id"],
                    "ts": now_iso(),
                    **enriched,
                }
                validate(instance=out, schema=ENRICHED_EVENT_SCHEMA)
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
                # Transient-ish: rate limits etc. Anthropic returns 429 with retry-after
                # header; in prod you should honor it. :contentReference[oaicite:3]{index=3}
                conn.rollback()
                dlq(producer, msg, f"unexpected: {e}")
                _mark_failed(conn, msg)
                consumer.commit(message=msg, asynchronous=False)
                print(f"[DLQ] unexpected: {e}")


if __name__ == "__main__":
    main()
