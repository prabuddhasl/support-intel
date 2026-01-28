# TODO

## Near-term
- Add validation and normalization for file types (reject huge files, enforce size limit).
- Expose a debug endpoint to inspect recent KB ingestions.

## Retrieval improvements
- Add embeddings + vector search (pgvector or external vector DB).
- Evaluate semantic chunking for long unstructured docs.
- Explore QA-style chunking for high-value sections (SLA, refunds, escalations).
- Make chunking token-aware and align chunk sizes with the chosen Claude model tokenizer.

## Enrichment pipeline
- Inject top-k KB chunks into Claude prompt with strict schema validation.
- Add prompt/version tracking and re-enrichment via Kafka replay.
