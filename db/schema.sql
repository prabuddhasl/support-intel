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
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_events (
  event_id TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);
