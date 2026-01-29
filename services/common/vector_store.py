from collections.abc import Iterable, Sequence

from pgvector.psycopg import register_vector


def _rows_to_chunks(rows: Sequence[tuple]) -> list[dict]:
    return [
        {
            "id": row[0],
            "doc_id": row[1],
            "chunk_index": row[2],
            "heading_path": row[3],
            "content": row[4],
            "title": row[5],
            "source": row[6],
            "source_url": row[7],
        }
        for row in rows
    ]


def insert_kb_chunks_with_embeddings(
    conn,
    doc_id: int,
    chunks: list[dict],
    embeddings: Sequence[Iterable[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")
    register_vector(conn)
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
        conn.execute(
            "INSERT INTO kb_chunks(doc_id, chunk_index, heading_path, content, embedding)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                doc_id,
                idx,
                chunk.get("heading_path"),
                chunk["content"],
                list(embedding),
            ),
        )


def update_chunk_embedding(conn, chunk_id: int, embedding: Iterable[float]) -> None:
    register_vector(conn)
    conn.execute(
        "UPDATE kb_chunks SET embedding=%s WHERE id=%s",
        (list(embedding), chunk_id),
    )


def search_similar_chunks(conn, query_embedding: Iterable[float], top_k: int = 5) -> list[dict]:
    register_vector(conn)
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.doc_id,
            c.chunk_index,
            c.heading_path,
            c.content,
            d.title,
            d.source,
            d.source_url
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.doc_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <-> (%s)::vector
        LIMIT %s
        """,
        (list(query_embedding), top_k),
    ).fetchall()

    return _rows_to_chunks(rows)


def search_keyword_chunks(conn, query_text: str, top_k: int = 5) -> list[dict]:
    if not query_text.strip():
        return []
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.doc_id,
            c.chunk_index,
            c.heading_path,
            c.content,
            d.title,
            d.source,
            d.source_url
        FROM kb_chunks c
        JOIN kb_documents d ON d.id = c.doc_id
        WHERE c.content_tsv @@ plainto_tsquery('english', %s)
        ORDER BY ts_rank_cd(c.content_tsv, plainto_tsquery('english', %s)) DESC, c.id ASC
        LIMIT %s
        """,
        (query_text, query_text, top_k),
    ).fetchall()

    return _rows_to_chunks(rows)
