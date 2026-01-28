# Support Intel - AI-Powered Support Ticket Enrichment

An event-driven system that uses Claude AI to automatically analyze and enrich customer support tickets with actionable insights.

## What It Does

The system consumes support ticket events from Kafka, uses Claude AI to analyze them, and produces enriched tickets with:
- **Summary**: Concise overview of the issue
- **Category**: Classification (e.g., technical_issue, billing, feature_request)
- **Sentiment**: Customer emotional tone (positive, negative, neutral)
- **Risk Score**: 0-1 urgency indicator (higher = more urgent)
- **Suggested Reply**: AI-generated response for support agents

## Architecture

```
┌─────────────────┐
│   REST API      │ ← POST /tickets (create)
│   (FastAPI)     │ ← GET /tickets (query)
└────┬────────┬───┘
     │        │
     │        └──────────────────┐
     ↓                           ↓
Kafka Topic              PostgreSQL Database
(support.tickets.v1)     (enriched_tickets)
     ↓                           ↑
Enricher Service                 │
(Claude AI)                      │
     ↓                           │
PostgreSQL ──────────────────────┘
     ↓
Kafka Topic
(support.enriched.v1)
```

## Prerequisites

- Docker Desktop installed and running
- Anthropic API key (copy `.env.example` to `.env`)
- Python 3.11+ (for local development)

## Setup Instructions

### 1. Configure Environment

Copy `.env.example` to `.env` and set required values.
Minimum to run:
- `ANTHROPIC_API_KEY`
- `EMBEDDING_MODEL` (default: `BAAI/bge-small-en-v1.5`)
- `KB_TOP_K` (default: `5`)

Note: embeddings are computed locally via `sentence-transformers`. The first run will download the model
to your Hugging Face cache (typically `~/.cache/huggingface`).

### 2. Install Python Dependencies (Local Dev)

```bash
pip install -r requirements-dev.txt
```

### 3. Start the Services (Recommended)

```bash
cd /Users/prabuddhalakshminarayana/Desktop/support-intel

# Clean start: rebuild, wait for DB, create Kafka topics, run migrations
make start
```

### 4. Start the Services (Manual)

```bash
cd /Users/prabuddhalakshminarayana/Desktop/support-intel

# Start all services (Kafka, PostgreSQL, API, Enricher, frontends)
docker compose up -d
```

### 5. Verify Services are Running

```bash
docker compose ps
```

You should see:
- `kafka` - Running on port 29092
- `support-intel-postgres-1` - Running on port 5432
- `support-intel-migrate-1` - Runs Alembic migrations then exits
- `support-intel-enricher-1` - Running
- `support-intel-api-1` - Running on port 8000
- `pgadmin` - Running on port 5050 (optional DB GUI)

## Developer Ergonomics (Make Targets)

Common shortcuts:
```
make up              # docker compose up -d --build
make down            # docker compose down
make reset           # docker compose down -v
make start           # clean slate + rebuild + wait for DB + create topics + migrate + start enricher
make dev             # start + tail api/enricher logs
make ps              # docker compose ps
make logs            # tail logs
make logs-enricher   # tail enricher logs
make enricher        # start only enricher
make status          # docker compose ps (alias)
make create-topics   # create Kafka topics if missing
make health          # check API, DB, and Kafka status
make doctor          # env + tooling checks
make seed            # seed sample KB + tickets
make clean           # remove python cache files
```

Tooling:
```
make install-python-dev
make install-frontend
make install-customer-portal
```

Quality checks:
```
make lint
make test
```

## Database Migrations

Migrations are managed with Alembic (see `migrations/versions`).

### Run migrations locally
```
export DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/supportintel
make migrate
```

### Existing databases (pre-migrations)
If your database was created via `db/schema.sql`, Alembic will try to create tables that already exist.
Use one of these:
1) Fresh DB (recommended for local dev): drop the DB volume and rerun migrations.
2) Mark as migrated: `alembic stamp head`

### Create a new migration
```
alembic revision -m "describe change"
```

### Migration 101 (example)
Goal: add a `sla_breach` boolean to `enriched_tickets`.

1) Create a migration file:
```
alembic revision -m "add sla_breach to enriched_tickets"
```

2) Edit the new migration:
```py
def upgrade() -> None:
    op.add_column("enriched_tickets", sa.Column("sla_breach", sa.Boolean, server_default="false"))

def downgrade() -> None:
    op.drop_column("enriched_tickets", "sla_breach")
```

3) Apply it:
```
make migrate
```

## Service Contracts

These are stable, versioned contracts. Breaking changes require a schema version bump and a migration plan.

### API Error Contract

All non-2xx responses return a consistent error payload.

Shape:
```
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object | array | null",
    "request_id": "string | null"
  }
}
```

Notes:
- `code` is a stable identifier (e.g., `validation_error`, `http_404`, `http_500`).
- `message` is human-readable and safe to surface.
- `details` may include validation errors or extra context.
- `request_id` is echoed from `X-Request-Id` or generated server-side.
- API responses include `X-Request-Id` header.

### Kafka Event Schemas

#### Ticket Event (support.tickets.v1)

Versioned schema: `TICKET_EVENT_SCHEMA_VERSION = 1`

Required fields:
- `schema_version` (int, enum [1])
- `event_id` (string)
- `ticket_id` (string)
- `ts` (string, ISO 8601)
- `subject` (string)
- `body` (string)
- `channel` (string)
- `priority` (string)

Optional fields:
- `customer_id` (string)

Compatibility rules:
- New optional fields are backward compatible.
- Removing/renaming required fields is breaking and requires a new version.
- Events must include `schema_version`.

#### Enriched Event (support.enriched.v1)

Versioned schema: `ENRICHED_EVENT_SCHEMA_VERSION = 1`

Required fields:
- `schema_version` (int, enum [1])
- `event_id` (string)
- `ticket_id` (string)
- `ts` (string, ISO 8601)
- `summary` (string)
- `category` (string)
- `sentiment` (string)
- `risk` (number 0..1)
- `suggested_reply` (string)

Compatibility rules:
- New optional fields are backward compatible.
- Removing/renaming required fields is breaking and requires a new version.
- Events must include `schema_version`.

### 3. Check Enricher Logs

```bash
# View real-time logs
docker compose logs -f enricher

# View last 50 lines
docker compose logs enricher --tail=50
```

### 4. Open pgAdmin (Optional DB GUI)

```bash
# Start pgAdmin if you want a web UI for Postgres
docker compose up -d pgadmin
```

Open `http://localhost:5050` and login with:
- Email: `admin@example.com`
- Password: `admin`

Then add a server:
- Host: `postgres`
- Port: `5432`
- Username: `app`
- Password: `app`
- DB: `supportintel`

## Using the API

The REST API is available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

### Available Endpoints

**Create a New Ticket:**
```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Cannot login to account",
    "body": "Getting invalid password errors",
    "channel": "email",
    "priority": "high",
    "customer_id": "CUST-123"
  }'
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Upload Knowledge Base Document (PDF/DOCX/TXT/MD):**
```bash
curl -X POST "http://localhost:8000/kb/upload?source=help_center&source_url=https://docs.example.com" \
  -F "file=@/path/to/your-doc.pdf"
```
Sample KB file for testing: `kb/sample_kb.md`
Max upload size: 10 MB

**Search Knowledge Base (keyword):**
```bash
curl "http://localhost:8000/kb/search?q=refund&limit=5"
```

**List All Tickets:**
```bash
curl http://localhost:8000/tickets
```

**Filter High-Risk Tickets:**
```bash
curl "http://localhost:8000/tickets?risk_min=0.7"
```

**Filter by Category:**
```bash
curl "http://localhost:8000/tickets?category=technical_issue"
```

**Filter by Sentiment:**
```bash
curl "http://localhost:8000/tickets?sentiment=negative"
```

**Get Specific Ticket:**
```bash
curl http://localhost:8000/tickets/TICKET-999
```

**Get Analytics Summary:**
```bash
curl http://localhost:8000/analytics/summary
```

**List Available Categories:**
```bash
curl http://localhost:8000/categories
```

**List Available Sentiments:**
```bash
curl http://localhost:8000/sentiments
```

### API Response Examples

**Create Ticket Response:**
```json
{
  "event_id": "evt-637d01b22a12",
  "ticket_id": "TICKET-681DE1B1",
  "message": "Ticket created and queued for enrichment",
  "status": "pending"
}
```

**Ticket List Response:**
```json
{
  "tickets": [
    {
      "ticket_id": "TICKET-999",
      "last_event_id": "test-67890",
      "summary": "User unable to access dashboard...",
      "category": "technical_issue",
      "sentiment": "negative",
      "risk": 0.75,
      "suggested_reply": "Thank you for reporting...",
      "updated_at": "2026-01-27T00:55:46.396342Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**Analytics Summary Response:**
```json
{
  "total_tickets": 1,
  "avg_risk": 0.75,
  "high_risk_count": 1,
  "by_category": {
    "technical_issue": 1
  },
  "by_sentiment": {
    "negative": 1
  }
}
```

## Testing the System

### Send a Test Ticket

```bash
# Create a test ticket file
cat > /tmp/test_ticket.json <<'EOF'
{
  "event_id": "test-12345",
  "ticket_id": "TICKET-001",
  "ts": "2026-01-26T00:00:00Z",
  "subject": "Cannot login to my account",
  "body": "I've been trying to log in for the past 30 minutes but keep getting 'invalid password' errors. I'm sure my password is correct. This is urgent as I need to access my account for an important meeting.",
  "channel": "email",
  "priority": "high",
  "customer_id": "CUST-456"
}
EOF

# Send it to Kafka
docker cp /tmp/test_ticket.json kafka:/tmp/
docker exec kafka bash -c 'cat /tmp/test_ticket.json | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic support.tickets.v1'
```

### Verify Processing

**Check the database:**
```bash
docker exec support-intel-postgres-1 psql -U app -d supportintel -c "
  SELECT
    ticket_id,
    category,
    sentiment,
    ROUND(risk::numeric, 2) as risk,
    summary,
    LEFT(suggested_reply, 100) as reply_preview
  FROM enriched_tickets
  ORDER BY updated_at DESC
  LIMIT 5;
"
```

**Check the enriched output topic:**
```bash
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic support.enriched.v1 \
  --from-beginning \
  --max-messages 5 \
  --timeout-ms 3000 2>&1 | head -20
```

**Check for failed messages (Dead Letter Queue):**
```bash
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9092 \
  --topic support.dlq.v1 \
  --from-beginning \
  --max-messages 10 \
  --timeout-ms 2000 2>&1 | grep -v "TimeoutException"
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in values for local runs.
Required vars are grouped by service in `.env.example`.
Note: the enricher uses `ENRICHER_TOPIC_IN` to avoid clashing with the API's `TOPIC_IN`.
Embeddings are local by default; set `EMBEDDING_MODEL` to change the model used for both KB chunks and ticket queries.

### Docker Compose Configuration

See `docker-compose.yml` for service configuration:
- **Kafka**: Bootstrap server at `kafka:9092`
- **Topics**:
  - `support.tickets.v1` (input)
  - `support.enriched.v1` (output)
  - `support.dlq.v1` (dead letter queue)
- **Database**: PostgreSQL at `postgres:5432`
- **Model**: `claude-sonnet-4-5-20250929`
- **Build context**: Services are built from the repo root so shared `services/` modules are available in containers.
  - API command: `uvicorn services.api.app:app`
  - Enricher command: `python -m services.enricher.app`

## Database Schema

**enriched_tickets table:**
```sql
ticket_id TEXT PRIMARY KEY
last_event_id TEXT
summary TEXT
category TEXT
sentiment TEXT
risk DOUBLE PRECISION
suggested_reply TEXT
updated_at TIMESTAMPTZ
```

**processed_events table:**
```sql
event_id TEXT PRIMARY KEY
processed_at TIMESTAMPTZ
```

## Message Schema

### Input: support.tickets.v1

```json
{
  "event_id": "string (min 8 chars)",
  "ticket_id": "string",
  "ts": "ISO 8601 timestamp",
  "subject": "string",
  "body": "string",
  "channel": "email|chat|phone",
  "priority": "low|normal|high|critical",
  "customer_id": "string"
}
```

### Output: support.enriched.v1

```json
{
  "event_id": "string",
  "ticket_id": "string",
  "ts": "ISO 8601 timestamp",
  "summary": "string",
  "category": "string",
  "sentiment": "string",
  "risk": 0.0-1.0,
  "suggested_reply": "string"
}
```

## Common Operations

### Stop Services
```bash
docker compose down
```

### Restart Services
```bash
docker compose restart
```

### Rebuild Services After Code Changes
```bash
# Rebuild enricher
docker compose up -d --build enricher

# Rebuild API
docker compose up -d --build api

# Rebuild all services
docker compose up -d --build
```

### View Kafka Topics
```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --list
```

### Check Consumer Group Status
```bash
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe \
  --group support-enricher
```

### Connect to PostgreSQL
```bash
docker exec -it support-intel-postgres-1 psql -U app -d supportintel
```

### Clear All Data (Reset)
```bash
# Stop services
docker compose down

# Remove volumes (deletes all data)
docker volume rm support-intel_postgres-data 2>/dev/null || true

# Restart
docker compose up -d
```

## Troubleshooting

### Enricher Not Processing Messages

**Check if API key is set:**
```bash
docker exec support-intel-enricher-1 python -c "import os; print('API Key:', 'SET' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET')"
```

**Check consumer group lag:**
```bash
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe \
  --group support-enricher
```

### View Python Dependencies
```bash
docker exec support-intel-enricher-1 pip list
```

### Check Enricher Container Logs
```bash
docker logs support-intel-enricher-1 --tail=100
```

## Development

### Local Python Setup

```bash
pip install -r requirements-dev.txt
```

### Local Node Setup

Use `.nvmrc` to align Node.js versions:
```bash
nvm use
```

### Running Tests

```bash
pytest
```

### Testing Strategy

**Unit tests**
- Pure logic: chunking, schema validation, parsing utilities.
- Run with `pytest` (default).

**Contract tests**
- Verify Kafka event schemas (input + enriched) are stable and versioned.
- Run with `pytest services/common/tests/test_event_contracts.py`.

**Integration tests**
- Exercise real DB read/write with a live Postgres instance.
- Run with:
```
RUN_INTEGRATION_TESTS=1 DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/supportintel \
pytest services/api/tests/test_integration_api_db.py
```

### Linting & Type Checking

Python:
```
ruff check .
black .
mypy services
```

Frontends:
```
cd frontend && npm run lint
cd ../customer-portal && npm run lint
```

## Project Structure

```
support-intel/
├── docker-compose.yml          # Service orchestration
├── .env.example                # Sample environment variables
├── .env                        # Local environment (not committed)
├── db/
│   └── schema.sql             # PostgreSQL schema
├── services/
│   ├── common/
│   │   └── schemas.py         # Shared schemas/constants
│   ├── enricher/
│   │   ├── app.py             # Main enricher service
│   │   ├── config.py          # Enricher config
│   │   ├── requirements.txt    # Python dependencies
│   │   ├── requirements-test.txt # Test dependencies
│   │   └── Dockerfile         # Container definition
│   ├── api/
│   │   ├── app.py             # REST API service (FastAPI)
│   │   ├── config.py          # API config
│   │   ├── requirements.txt    # Python dependencies
│   │   ├── requirements-test.txt # Test dependencies
│   │   └── Dockerfile         # Container definition
│   └── __init__.py            # Package marker
├── frontend/                  # Operator dashboard
├── customer-portal/           # Customer-facing portal
├── pytest.ini                 # Pytest config
└── README.md                  # This file
```

## Key Features

- ✅ **Event-driven architecture** with Kafka
- ✅ **Idempotent processing** - Prevents duplicate processing
- ✅ **Dead Letter Queue** - Failed messages don't block the pipeline
- ✅ **Transactional consistency** - Database commits tied to Kafka offsets
- ✅ **Schema validation** - Invalid messages rejected early
- ✅ **AI-powered enrichment** - Claude Sonnet 4.5 analysis

## Notes

- The enricher processes messages with **manual offset commits** to ensure exactly-once processing
- Messages are deduplicated using the `processed_events` table
- Python output is unbuffered in the container, so logs appear in real-time
- The system uses Claude's latest Sonnet 4.5 model for high-quality analysis
- Risk scores above 0.7 typically indicate urgent issues requiring immediate attention

## Next Steps (Future Enhancements)

- [ ] Add a ticket-producer service for testing
- [ ] Add metrics and monitoring (Prometheus/Grafana)
- [ ] Implement retry logic with exponential backoff
- [ ] Add support for ticket attachments/images
- [ ] Create a web UI for viewing enriched tickets
- [ ] Add batch processing for high-volume scenarios
