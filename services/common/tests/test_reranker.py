from unittest.mock import MagicMock

import services.common.reranker as reranker


def test_rerank_chunks_orders_by_score(monkeypatch):
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.2, 0.9, 0.5]
    monkeypatch.setattr(reranker, "_get_model", lambda _name: fake_model)

    chunks = [
        {"title": "A", "heading_path": "H1", "content": "c1"},
        {"title": "B", "heading_path": "H2", "content": "c2"},
        {"title": "C", "heading_path": "H3", "content": "c3"},
    ]

    ranked = reranker.rerank_chunks("query", chunks, "model", top_n=2)
    assert ranked[0]["title"] == "B"
    assert ranked[1]["title"] == "C"
