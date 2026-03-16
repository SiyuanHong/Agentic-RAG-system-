import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.services.embedding import embed_texts
from app.services.reranker import rerank


@dataclass
class ChunkResult:
    id: str
    content: str
    metadata: dict
    score: float


RRF_K = 60


async def hybrid_search(
    query: str,
    kb_id: str,
    user_id: str,
    session: AsyncSession | None = None,
    top_k: int = 5,
) -> list[ChunkResult]:
    # Embed query
    query_embedding = (await embed_texts([query]))[0]

    owns_session = session is None
    if owns_session:
        session = async_session_factory()

    try:
        # Set RLS context so queries are tenant-scoped
        # PostgreSQL SET doesn't support parameterized queries ($1),
        # so we validate the UUID and use f-string
        sanitized_uid = str(uuid.UUID(user_id))  # validate UUID format
        await session.execute(
            text(f"SET app.current_user_id = '{sanitized_uid}'")
        )

        # Vector search — top 15
        # pgvector expects '[0.1,0.2,...]' string format
        vec_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        vector_sql = text("""
            SELECT id::text, content, chunk_metadata,
                   embedding <=> :query_vec AS distance
            FROM chunks
            WHERE kb_id = :kb_id
            ORDER BY distance ASC
            LIMIT 15
        """)
        vector_result = await session.execute(
            vector_sql,
            {
                "query_vec": vec_literal,
                "kb_id": kb_id,
            },
        )
        vector_rows = vector_result.fetchall()

        # BM25 search via pg_search — top 15
        bm25_sql = text("""
            SELECT id::text, content, chunk_metadata,
                   paradedb.score(id) AS score
            FROM chunks
            WHERE content @@@ :query
              AND kb_id = :kb_id
            ORDER BY score DESC
            LIMIT 15
        """)
        bm25_result = await session.execute(
            bm25_sql,
            {
                "query": query,
                "kb_id": kb_id,
            },
        )
        bm25_rows = bm25_result.fetchall()

    finally:
        if owns_session:
            await session.close()

    # RRF fusion
    scores: dict[str, float] = {}
    chunk_data: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        cid = row[0]
        scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
        chunk_data[cid] = {"content": row[1], "metadata": row[2] or {}}

    for rank, row in enumerate(bm25_rows):
        cid = row[0]
        scores[cid] = scores.get(cid, 0) + 1.0 / (RRF_K + rank + 1)
        chunk_data[cid] = {"content": row[1], "metadata": row[2] or {}}

    # Sort by RRF score, take top ~20 for reranking
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:20]

    if not sorted_ids:
        return []

    # Cohere rerank
    docs_for_rerank = [chunk_data[cid]["content"] for cid in sorted_ids]
    reranked = await rerank(query, docs_for_rerank, top_n=top_k)

    results = []
    for r in reranked:
        cid = sorted_ids[r["index"]]
        results.append(
            ChunkResult(
                id=cid,
                content=chunk_data[cid]["content"],
                metadata=chunk_data[cid]["metadata"],
                score=r["relevance_score"],
            )
        )
    return results
