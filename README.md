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

### 1. Start the Services

```bash
cd /Users/prabuddhalakshminarayana/Desktop/support-intel

# Start all services (Kafka, PostgreSQL, API, Enricher, frontends)
docker compose up -d
```

### 2. Verify Services are Running

```bash
docker compose ps
```

You should see:
- `kafka` - Running on port 29092
- `support-intel-postgres-1` - Running on port 5432
- `support-intel-enricher-1` - Running
- `support-intel-api-1` - Running on port 8000
- `pgadmin` - Running on port 5050 (optional DB GUI)

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
cd services/enricher
pip3 install -r requirements.txt

cd ../api
pip3 install -r requirements.txt
```

### Running Tests

```bash
pytest
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
