CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS enriched_tickets (
  ticket_id TEXT PRIMARY KEY,
  last_event_id TEXT,
  subject TEXT,
  body TEXT,
  channel TEXT,
  priority TEXT,
  customer_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  summary TEXT,
  category TEXT,
  sentiment TEXT,
  risk DOUBLE PRECISION,
  suggested_reply TEXT,
  citations JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_events (
  event_id TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kb_documents (
  id SERIAL PRIMARY KEY,
  filename TEXT NOT NULL,
  title TEXT,
  content_type TEXT,
  sha256 TEXT NOT NULL,
  size_bytes INTEGER,
  source TEXT,
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kb_chunks (
  id SERIAL PRIMARY KEY,
  doc_id INTEGER NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  heading_path TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(384),
  content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

CREATE INDEX IF NOT EXISTS kb_chunks_doc_id_idx ON kb_chunks(doc_id);
CREATE INDEX IF NOT EXISTS kb_chunks_content_tsv_idx ON kb_chunks USING GIN (content_tsv);

ALTER TABLE IF EXISTS kb_documents
  ADD COLUMN IF NOT EXISTS title TEXT,
  ADD COLUMN IF NOT EXISTS source_url TEXT;

ALTER TABLE IF EXISTS kb_chunks
  ADD COLUMN IF NOT EXISTS heading_path TEXT,
  ADD COLUMN IF NOT EXISTS embedding VECTOR(384),
  ADD COLUMN IF NOT EXISTS content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
