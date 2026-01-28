# TODO (Portfolio-grade roadmap)

## Phase 1 — Foundations (quality + contracts)
- Define service contracts: API schemas, Kafka message schema versions, error formats, and backward-compat rules.
- Add DB migrations (Alembic) instead of raw init SQL for evolving schema.
- Add test strategy: unit tests for chunking + schema validation, integration tests for API+DB, contract tests for Kafka events.
- Add type safety + linting: mypy/ruff/black for Python; ESLint + type-aware rules for frontend.
- Add local dev ergonomics: Makefile or task runner, .env.example, documented setup steps.

## Phase 2 — Retrieval-augmented enrichment (core value)
- Add embeddings storage and retrieval (pgvector in Postgres or external vector DB).
- Extend KB ingestion to generate and store chunk embeddings with metadata (title, section path, source URL).
- Implement retrieval in the enricher: embed ticket, fetch top-k chunks, inject into Claude prompt, strict JSON/schema validation.
- Add prompt/version tracking for traceability and replay.

## Phase 3 — Reliability + observability
- Add structured logging (JSON), request IDs, and correlation IDs across API -> Kafka -> enricher.
- Add metrics (Prometheus-style) plus readiness/liveness endpoints.
- Add DLQ monitoring: retry policy, alerting hooks, and dashboard view of failed enrichments.
- Add backpressure/rate-limit handling for Anthropic API and Kafka commits.
- Add requeue/retry workflow for failed tickets (manual + automated replay from DLQ).

## Phase 4 — Security + compliance
- Secrets management (env + validation), config validation (pydantic settings).
- Input validation hardening (file upload type/size, content sanitization).
- Auth for APIs (JWT or API key), tighten CORS to known domains.
- Audit logging for KB ingest and ticket updates.

## Phase 5 — Portfolio polish
- Add UI screens: KB ingestion status, search relevance preview, enrichment trace view.
- Add SLOs + runbook docs (DLQ spikes, API latency).
- CI/CD pipeline (lint/test/build, container scan).
- Add ADRs (Architecture Decision Records) to document major choices.
