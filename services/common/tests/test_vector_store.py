from unittest.mock import MagicMock

from services.common import vector_store


def test_search_similar_chunks_executes_vector_query(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (1, 10, 0, "A > B", "Chunk text", "Doc Title", "help_center", "https://example.com"),
    ]
    conn.execute.return_value = cursor

    registered = {"conn": None}

    def _register_vector(c):
        registered["conn"] = c

    monkeypatch.setattr(vector_store, "register_vector", _register_vector)

    results = vector_store.search_similar_chunks(conn, [0.1, 0.2], top_k=3)

    assert registered["conn"] is conn
    sql = conn.execute.call_args[0][0]
    assert "ORDER BY c.embedding <-> (%s)::vector" in sql
    assert conn.execute.call_args[0][1] == ([0.1, 0.2], 3)
    assert results == [
        {
            "id": 1,
            "doc_id": 10,
            "chunk_index": 0,
            "heading_path": "A > B",
            "content": "Chunk text",
            "title": "Doc Title",
            "source": "help_center",
            "source_url": "https://example.com",
        }
    ]


def test_update_chunk_embedding_registers_vector(monkeypatch):
    conn = MagicMock()
    registered = {"conn": None}

    def _register_vector(c):
        registered["conn"] = c

    monkeypatch.setattr(vector_store, "register_vector", _register_vector)

    vector_store.update_chunk_embedding(conn, 42, [0.1, 0.2, 0.3])

    assert registered["conn"] is conn
    conn.execute.assert_called_once()
    sql = conn.execute.call_args[0][0]
    params = conn.execute.call_args[0][1]
    assert "UPDATE kb_chunks SET embedding=%s WHERE id=%s" in sql
    assert params == ([0.1, 0.2, 0.3], 42)
