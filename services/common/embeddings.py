from __future__ import annotations

from collections.abc import Iterable

from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_model_name: str | None = None


def _get_model(model_name: str) -> SentenceTransformer:
    global _model, _model_name
    if _model is None or _model_name != model_name:
        _model = SentenceTransformer(model_name)
        _model_name = model_name
    return _model


def embed_texts(texts: Iterable[str], model_name: str) -> list[list[float]]:
    model = _get_model(model_name)
    embeddings = model.encode(list(texts), normalize_embeddings=True)
    return embeddings.tolist()


def embed_text(text: str, model_name: str) -> list[float]:
    return embed_texts([text], model_name=model_name)[0]
