from __future__ import annotations

from sentence_transformers import CrossEncoder

_model: CrossEncoder | None = None
_model_name: str | None = None


def _get_model(model_name: str) -> CrossEncoder:
    global _model, _model_name
    if _model is None or _model_name != model_name:
        _model = CrossEncoder(model_name)
        _model_name = model_name
    return _model


def _chunk_text(chunk: dict) -> str:
    title = chunk.get("title") or ""
    heading = chunk.get("heading_path") or ""
    content = chunk.get("content") or ""
    parts = [p for p in [title, heading, content] if p]
    return "\n".join(parts).strip()


def rerank_chunks(
    query: str,
    chunks: list[dict],
    model_name: str,
    top_n: int,
) -> list[dict]:
    if not chunks:
        return []
    model = _get_model(model_name)
    pairs: list[tuple[str, str]] = [(query, _chunk_text(chunk)) for chunk in chunks]
    scores = model.predict(pairs)
    scored = list(zip(scores, chunks, strict=True))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:top_n]]
