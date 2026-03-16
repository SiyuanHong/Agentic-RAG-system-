import cohere

from app.core.config import settings

_client = cohere.AsyncClientV2(
    api_key=settings.COHERE_API_KEY,
    **({"base_url": settings.COHERE_BASE_URL} if settings.COHERE_BASE_URL else {}),
)


async def rerank(
    query: str, documents: list[str], top_n: int = 5
) -> list[dict]:
    if not documents:
        return []

    response = await _client.rerank(
        model=settings.COHERE_RERANK_MODEL,
        query=query,
        documents=documents,
        top_n=min(top_n, len(documents)),
    )
    return [
        {"index": r.index, "relevance_score": r.relevance_score}
        for r in response.results
    ]
