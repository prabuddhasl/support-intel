# TODO (Portfolio-grade roadmap)

## Phase 1 — Foundations (quality + contracts)
- [x] Define service contracts: API schemas, Kafka message schema versions, error formats, and backward-compat rules.
- [x] Add DB migrations (Alembic) instead of raw init SQL for evolving schema.
- [x] Add test strategy: unit tests for chunking + schema validation, integration tests for API+DB, contract tests for Kafka events.
- [x] Add type safety + linting: mypy/ruff/black for Python; ESLint + type-aware rules for frontend.
- [x] Add local dev ergonomics: Makefile or task runner, .env.example, documented setup steps.
- [x] Simplify setup to a single Python env and consolidated root requirements + README steps.

## Phase 2 — Retrieval-augmented enrichment (core value)
- [ ] Embeddings + retrieval foundations:
  - Add embeddings storage and retrieval (pgvector in Postgres or external vector DB).
  - Extend KB ingestion to generate and store chunk embeddings with metadata (title, section path, source URL).
  - Implement retrieval in the enricher: embed ticket, fetch top-k chunks, inject into Claude prompt, strict JSON/schema validation.
  - Make embedding provider pluggable and model selectable (document tradeoffs and candidates).
- [ ] Enrichment quality + grounding:
  - Prompt upgrade: strict response template (acknowledge → 2–4 bullet steps → next step).
  - Enforce “use KB only; if missing, ask 1–2 clarifying questions.”
  - KB context discipline: keep top-k small (5–8) and cap context length.
  - Output normalization + schema: enums for category/sentiment and post-output normalization.
- [ ] Citations + provenance:
  - Store chunk IDs/titles from retrieval.
  - Include citations: [{chunk_id, title, heading_path}].
  - Add citations array to enriched event schema.
  - Persist citations JSON in enriched_tickets.
- [ ] Spam/irrelevant detection:
  - Decide approach: heuristic keywords vs embedding similarity (KB centroid threshold).
  - Apply in enricher before Claude.
  - If spam: category=general or spam, low risk, short reply (“out of scope”).
  - Add is_spam boolean in DB + enriched event schema.
- [ ] KB lifecycle + continuous updates:
  - Version KB documents (immutable versions or is_current flag) to preserve history while serving latest content.
  - Plan continuous KB updates (e.g., Gong transcripts) ingestion.
    - Decisions: Kafka stream vs scheduled batch; dedup strategy (hash + similarity threshold); recency weighting; versioning/is_current policy; retention window for old chunks.
- [ ] RAG enhancements (advanced):
  - Reranking (cross-encoder or LLM scorer) on top-k retrieval.
  - Hybrid search (vector + keyword).
  - Metadata filtering (source, recency, version).
  - Chunking strategy improvements (section-aware, overlap tuning).
  - Context compression/summarization.
  - Query reformulation for better retrieval.
  - Recency weighting.
  - Attribution/self-check (require citations or ask clarifying questions).
- [ ] Traceability + replay:
  - Add prompt/version tracking for traceability and replay.
  - Include prompt_version/model_version/event_id in enriched events and persist for replay.
  - Support replay from support.tickets.v1 to re-enrich after retrieval/prompt changes.

## Phase 3 — Reliability + observability
- [ ] Add structured logging (JSON), request IDs, and correlation IDs across API -> Kafka -> enricher.
- [ ] Add metrics (Prometheus-style) plus readiness/liveness endpoints.
- [ ] Add DLQ monitoring: retry policy, alerting hooks, and dashboard view of failed enrichments.
- [ ] Add backpressure/rate-limit handling for Anthropic API and Kafka commits.
- [ ] Add requeue/retry workflow for failed tickets (manual + automated replay from DLQ).
- [ ] Propagate request_id/event_id end-to-end and log them on every hop.
- [ ] Track Kafka consumer lag, throughput, and processing latency (P50/P95).
- [ ] Add a DLQ replay tool that republishes to support.tickets.v1 with failure metadata.
- [ ] Ensure at-least-once semantics by committing offsets only after DB write.

## Phase 4 — Security + compliance
- [ ] Secrets management (env + validation), config validation (pydantic settings).
- [ ] Input validation hardening (file upload type/size, content sanitization).
- [ ] Auth for APIs (JWT or API key), tighten CORS to known domains.
- [ ] Audit logging for KB ingest and ticket updates.

## Phase 5 — Portfolio polish
- [ ] Add UI screens: KB ingestion status, search relevance preview, enrichment trace view.
- [ ] Add SLOs + runbook docs (DLQ spikes, API latency).
- [ ] CI/CD pipeline (lint/test/build, container scan).
- [ ] Add ADRs (Architecture Decision Records) to document major choices.
- [ ] Document Kafka ops runbooks (lag spikes, DLQ growth, replay procedures).
- [ ] Add UI view for DLQ/failed enrichments with manual replay action.
