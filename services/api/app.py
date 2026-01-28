import hashlib
import io
import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

import psycopg
from confluent_kafka import Producer
from docx import Document
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jsonschema import ValidationError, validate
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

if TYPE_CHECKING:
    from services.api.config import BOOTSTRAP, DATABASE_URL, EMBEDDING_MODEL, TOPIC_IN
    from services.common.schemas import TICKET_EVENT_SCHEMA, TICKET_EVENT_SCHEMA_VERSION
else:
    try:
        from services.api.config import BOOTSTRAP, DATABASE_URL, EMBEDDING_MODEL, TOPIC_IN
        from services.common.schemas import TICKET_EVENT_SCHEMA, TICKET_EVENT_SCHEMA_VERSION
    except Exception:  # pragma: no cover - fallback for direct script execution
        from common.schemas import TICKET_EVENT_SCHEMA, TICKET_EVENT_SCHEMA_VERSION
        from config import BOOTSTRAP, DATABASE_URL, EMBEDDING_MODEL, TOPIC_IN

from services.common.embeddings import embed_texts
from services.common.vector_store import insert_kb_chunks_with_embeddings

# Initialize Kafka producer
producer = Producer({"bootstrap.servers": BOOTSTRAP})

app = FastAPI(
    title="Support Intel API",
    description="REST API for querying AI-enriched support tickets",
    version="1.0.0",
)

# Enable CORS for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


def _error_payload(request: Request, code: str, message: str, details=None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "Request failed")
        details = detail
    else:
        message = str(detail)
        details = None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(request, f"http_{exc.status_code}", message, details),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            request, "validation_error", "Request validation failed", exc.errors()
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_payload(request, "internal_error", "Internal server error"),
    )


# Request models
class CreateTicketRequest(BaseModel):
    ticket_id: str | None = Field(None, description="Ticket ID (auto-generated if not provided)")
    subject: str = Field(..., min_length=1, description="Ticket subject")
    body: str = Field(..., min_length=1, description="Ticket body/description")
    channel: str = Field(..., description="Channel (email, chat, phone, etc.)")
    priority: str = Field(..., description="Priority (low, normal, high, critical)")
    customer_id: str | None = Field(None, description="Customer ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject": "Cannot login to account",
                "body": "I've been trying to log in but keep getting errors",
                "channel": "email",
                "priority": "high",
                "customer_id": "CUST-123",
            }
        }
    )


class CreateTicketResponse(BaseModel):
    event_id: str
    ticket_id: str
    message: str
    status: str


# Response models
class EnrichedTicket(BaseModel):
    ticket_id: str
    last_event_id: str | None
    subject: str | None
    body: str | None
    channel: str | None
    priority: str | None
    customer_id: str | None
    status: str
    summary: str | None
    category: str | None
    sentiment: str | None
    risk: float | None
    suggested_reply: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    tickets: list[EnrichedTicket]
    total: int
    page: int
    page_size: int


class AnalyticsSummary(BaseModel):
    total_tickets: int
    avg_risk: float
    high_risk_count: int
    by_category: dict
    by_sentiment: dict


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str


# Database connection helper
def get_db_connection():
    try:
        return psycopg.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}") from e


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _file_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _safe_filename(filename: str) -> str:
    basename = os.path.basename(filename or "")
    return basename[:200] if basename else "upload"


def _extract_text(file_bytes: bytes, filename: str) -> str:
    ext = _file_extension(filename)
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    if ext == ".docx":
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    if ext in {".txt", ".md"}:
        return file_bytes.decode("utf-8", errors="replace").strip()
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


class _Paragraph(TypedDict):
    text: str
    heading_path: str
    is_heading: bool


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    lines = [line.rstrip() for line in text.splitlines()]
    paragraphs: list[_Paragraph] = []
    current: list[str] = []
    heading_stack: list[tuple[int, str]] = []

    def current_heading_path() -> str:
        return " > ".join([h[1] for h in heading_stack if h[1]])

    def flush_paragraph(is_heading: bool = False):
        nonlocal current
        if current:
            paragraphs.append(
                {
                    "text": "\n".join(current).strip(),
                    "heading_path": current_heading_path(),
                    "is_heading": is_heading,
                }
            )
            current = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            flush_paragraph()
            level = len(stripped.split()[0])
            heading_text = stripped.lstrip("#").strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading_text))
            paragraphs.append(
                {
                    "text": stripped,
                    "heading_path": current_heading_path(),
                    "is_heading": True,
                }
            )
            continue
        if stripped == "":
            flush_paragraph()
            continue
        current.append(stripped)
    flush_paragraph()

    chunks = []
    buf = ""
    buf_heading = ""

    def push_chunk(value: str, heading_path: str):
        if value.strip():
            chunks.append(
                {
                    "content": value.strip(),
                    "heading_path": heading_path,
                }
            )

    for para in paragraphs:
        heading_path = para["heading_path"]
        text_block = para["text"]

        if buf and heading_path and buf_heading and heading_path != buf_heading:
            push_chunk(buf, buf_heading)
            buf = ""
            buf_heading = ""

        if len(text_block) >= chunk_size:
            if buf:
                push_chunk(buf, buf_heading)
                buf = ""
                buf_heading = ""
            start = 0
            while start < len(text_block):
                end = min(start + chunk_size, len(text_block))
                push_chunk(text_block[start:end], heading_path)
                start = end - overlap
                if start < 0:
                    start = 0
                if end == len(text_block):
                    break
            continue

        if not buf:
            buf = text_block
            buf_heading = heading_path
            continue

        candidate = f"{buf}\n\n{text_block}"
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            push_chunk(buf, buf_heading)
            buf = text_block
            buf_heading = heading_path

    if buf:
        push_chunk(buf, buf_heading)

    return chunks


# Endpoints
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Support Intel API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "create_ticket": "POST /tickets",
            "list_tickets": "GET /tickets",
            "ticket_by_id": "/tickets/{ticket_id}",
            "analytics": "/analytics/summary",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.post("/tickets", response_model=CreateTicketResponse, status_code=201)
async def create_ticket(ticket: CreateTicketRequest):
    """
    Create a new support ticket and publish to Kafka for enrichment

    The ticket will be:
    1. Published to Kafka topic (support.tickets.v1)
    2. Picked up by enricher service
    3. Analyzed by Claude AI
    4. Stored in database with enrichments
    5. Available via GET /tickets endpoints

    Example:
    ```json
    {
      "subject": "Cannot access dashboard",
      "body": "Getting a blank page when I try to load my dashboard",
      "channel": "email",
      "priority": "high",
      "customer_id": "CUST-123"
    }
    ```
    """
    try:
        # Generate IDs if not provided
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        ticket_id = ticket.ticket_id or f"TICKET-{uuid.uuid4().hex[:8].upper()}"

        # Write raw ticket to DB immediately so it's visible via GET
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO enriched_tickets(
                  ticket_id, last_event_id, subject, body, channel, priority, customer_id, status,
                  created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW(), NOW())
                ON CONFLICT (ticket_id) DO UPDATE SET
                  last_event_id=EXCLUDED.last_event_id,
                  subject=EXCLUDED.subject,
                  body=EXCLUDED.body,
                  channel=EXCLUDED.channel,
                  priority=EXCLUDED.priority,
                  customer_id=EXCLUDED.customer_id,
                  status='pending',
                  updated_at=NOW()
                """,
                (
                    ticket_id,
                    event_id,
                    ticket.subject,
                    ticket.body,
                    ticket.channel,
                    ticket.priority,
                    ticket.customer_id,
                ),
            )
            conn.commit()

        # Build ticket event
        ticket_event = {
            "schema_version": TICKET_EVENT_SCHEMA_VERSION,
            "event_id": event_id,
            "ticket_id": ticket_id,
            "ts": datetime.now(UTC).isoformat(),
            "subject": ticket.subject,
            "body": ticket.body,
            "channel": ticket.channel,
            "priority": ticket.priority,
        }

        if ticket.customer_id:
            ticket_event["customer_id"] = ticket.customer_id

        # Validate event schema before publishing
        try:
            validate(instance=ticket_event, schema=TICKET_EVENT_SCHEMA)
        except ValidationError as e:
            raise HTTPException(status_code=500, detail=f"Ticket event invalid: {str(e)}") from e

        # Publish to Kafka for async enrichment
        producer.produce(
            TOPIC_IN,
            value=json.dumps(ticket_event).encode("utf-8"),
            callback=lambda err, msg: print(
                f"Delivery failed: {err}" if err else f"Delivered to {msg.topic()}"
            ),
        )
        producer.flush(timeout=5)

        return CreateTicketResponse(
            event_id=event_id,
            ticket_id=ticket_id,
            message="Ticket created and queued for enrichment",
            status="pending",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ticket: {str(e)}") from e


@app.post("/kb/upload", response_model=dict, status_code=201)
async def upload_knowledge_base_file(
    file: UploadFile = File(...),  # noqa: B008
    source: str | None = Query(None, description="Optional source label, e.g. 'help_center'"),
    source_url: str | None = Query(None, description="Optional source URL"),
):
    """
    Upload a knowledge base document (PDF/DOCX/TXT/MD), parse it server-side,
    and store chunked content in the database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    safe_name = _safe_filename(file.filename)
    ext = _file_extension(safe_name)
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large (max {MAX_UPLOAD_BYTES} bytes)"
        )

    if file.content_type:
        allowed_types = ALLOWED_CONTENT_TYPES.get(ext, set())
        # Swagger/clients may send octet-stream for text files; allow if extension is valid.
        if allowed_types and file.content_type not in allowed_types:
            if file.content_type != "application/octet-stream":
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported content type: {file.content_type}",
                )

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    text = _extract_text(file_bytes, safe_name)
    if not text:
        raise HTTPException(status_code=400, detail="No extractable text found")

    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No valid chunks produced")

    title = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
    if not title:
        title = file.filename

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM kb_documents WHERE sha256=%s",
            (sha256,),
        ).fetchone()
        if existing:
            return {
                "doc_id": existing[0],
                "status": "already_ingested",
                "sha256": sha256,
                "chunks": 0,
            }

        row = conn.execute(
            """
            INSERT INTO kb_documents(
              filename, title, content_type, sha256, size_bytes, source, source_url
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (safe_name, title, file.content_type, sha256, len(file_bytes), source, source_url),
        ).fetchone()
        doc_id = row[0]

        chunk_texts = [c["content"] for c in chunks]
        embeddings = embed_texts(chunk_texts, model_name=EMBEDDING_MODEL)
        insert_kb_chunks_with_embeddings(conn, doc_id, chunks, embeddings)
        conn.commit()

    return {
        "doc_id": doc_id,
        "status": "ingested",
        "sha256": sha256,
        "chunks": len(chunks),
        "bytes": len(file_bytes),
    }


@app.get("/kb/search", response_model=dict)
async def search_knowledge_base(
    q: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(5, ge=1, le=50, description="Max results"),
):
    """
    Simple keyword search over KB chunks (ILIKE).
    """
    pattern = f"%{q}%"
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.doc_id, c.chunk_index, c.content, d.filename, d.source
            FROM kb_chunks c
            JOIN kb_documents d ON d.id = c.doc_id
            WHERE c.content ILIKE %s
            ORDER BY c.id ASC
            LIMIT %s
            """,
            (pattern, limit),
        ).fetchall()

    results = [
        {
            "chunk_id": row[0],
            "doc_id": row[1],
            "chunk_index": row[2],
            "content": row[3],
            "filename": row[4],
            "source": row[5],
        }
        for row in rows
    ]

    return {"query": q, "count": len(results), "results": results}


@app.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    risk_min: float | None = Query(None, ge=0, le=1, description="Minimum risk score"),
    risk_max: float | None = Query(None, ge=0, le=1, description="Maximum risk score"),
    category: str | None = Query(None, description="Filter by category"),
    sentiment: str | None = Query(None, description="Filter by sentiment"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("updated_at", description="Sort field (updated_at, risk, ticket_id)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
):
    """
    Get list of enriched tickets with optional filtering and pagination

    Example queries:
    - /tickets?risk_min=0.7 - High risk tickets only
    - /tickets?sentiment=negative - Negative sentiment tickets
    - /tickets?category=billing&page=2 - Second page of billing tickets
    """
    with get_db_connection() as conn:
        # Build WHERE clause
        conditions: list[str] = []
        params: list[object] = []

        if risk_min is not None:
            conditions.append("risk >= %s")
            params.append(risk_min)

        if risk_max is not None:
            conditions.append("risk <= %s")
            params.append(risk_max)

        if category:
            conditions.append("category = %s")
            params.append(category)

        if sentiment:
            conditions.append("sentiment = %s")
            params.append(sentiment)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Validate sort parameters
        valid_sort_fields = ["updated_at", "risk", "ticket_id"]
        if sort_by not in valid_sort_fields:
            sort_by = "updated_at"

        if sort_order.lower() not in ["asc", "desc"]:
            sort_order = "desc"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM enriched_tickets {where_clause}"
        total = conn.execute(count_query, params).fetchone()[0]

        # Get paginated results
        offset = (page - 1) * page_size
        params_with_pagination: list[object] = params + [page_size, offset]

        query = f"""
            SELECT ticket_id, last_event_id, subject, body, channel, priority, customer_id, status,
                   summary, category, sentiment, risk, suggested_reply, created_at, updated_at
            FROM enriched_tickets
            {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT %s OFFSET %s
        """

        rows = conn.execute(query, params_with_pagination).fetchall()

        tickets = [
            EnrichedTicket(
                ticket_id=row[0],
                last_event_id=row[1],
                subject=row[2],
                body=row[3],
                channel=row[4],
                priority=row[5],
                customer_id=row[6],
                status=row[7],
                summary=row[8],
                category=row[9],
                sentiment=row[10],
                risk=row[11],
                suggested_reply=row[12],
                created_at=row[13],
                updated_at=row[14],
            )
            for row in rows
        ]

        return TicketListResponse(
            tickets=tickets,
            total=total,
            page=page,
            page_size=page_size,
        )


@app.get("/tickets/{ticket_id}", response_model=EnrichedTicket)
async def get_ticket(ticket_id: str):
    """Get a specific ticket by ID"""
    with get_db_connection() as conn:
        query = """
            SELECT ticket_id, last_event_id, subject, body, channel, priority, customer_id, status,
                   summary, category, sentiment, risk, suggested_reply, created_at, updated_at
            FROM enriched_tickets
            WHERE ticket_id = %s
        """
        row = conn.execute(query, (ticket_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

        return EnrichedTicket(
            ticket_id=row[0],
            last_event_id=row[1],
            subject=row[2],
            body=row[3],
            channel=row[4],
            priority=row[5],
            customer_id=row[6],
            status=row[7],
            summary=row[8],
            category=row[9],
            sentiment=row[10],
            risk=row[11],
            suggested_reply=row[12],
            created_at=row[13],
            updated_at=row[14],
        )


@app.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary():
    """
    Get analytics summary across all tickets

    Returns aggregated statistics including:
    - Total ticket count
    - Average risk score
    - High-risk ticket count (risk > 0.7)
    - Breakdown by category
    - Breakdown by sentiment
    """
    with get_db_connection() as conn:
        # Total tickets and average risk
        summary_query = """
            SELECT
                COUNT(*) as total,
                COALESCE(AVG(risk), 0) as avg_risk,
                COUNT(CASE WHEN risk > 0.7 THEN 1 END) as high_risk_count
            FROM enriched_tickets
        """
        summary_row = conn.execute(summary_query).fetchone()

        # By category
        category_query = """
            SELECT category, COUNT(*) as count
            FROM enriched_tickets
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """
        category_rows = conn.execute(category_query).fetchall()
        by_category = {row[0]: row[1] for row in category_rows}

        # By sentiment
        sentiment_query = """
            SELECT sentiment, COUNT(*) as count
            FROM enriched_tickets
            WHERE sentiment IS NOT NULL
            GROUP BY sentiment
            ORDER BY count DESC
        """
        sentiment_rows = conn.execute(sentiment_query).fetchall()
        by_sentiment = {row[0]: row[1] for row in sentiment_rows}

        return AnalyticsSummary(
            total_tickets=summary_row[0],
            avg_risk=round(float(summary_row[1] or 0), 3),
            high_risk_count=summary_row[2],
            by_category=by_category,
            by_sentiment=by_sentiment,
        )


@app.get("/categories", response_model=list[str])
async def get_categories():
    """Get list of all unique categories"""
    with get_db_connection() as conn:
        query = """
            SELECT DISTINCT category
            FROM enriched_tickets
            WHERE category IS NOT NULL
            ORDER BY category
        """
        rows = conn.execute(query).fetchall()
        return [row[0] for row in rows]


@app.get("/sentiments", response_model=list[str])
async def get_sentiments():
    """Get list of all unique sentiments"""
    with get_db_connection() as conn:
        query = """
            SELECT DISTINCT sentiment
            FROM enriched_tickets
            WHERE sentiment IS NOT NULL
            ORDER BY sentiment
        """
        rows = conn.execute(query).fetchall()
        return [row[0] for row in rows]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
