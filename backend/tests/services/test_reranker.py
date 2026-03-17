from unittest.mock import AsyncMock, MagicMock, patch


@patch("app.services.reranker._client")
async def test_rerank_empty_documents(mock_client):
    from app.services.reranker import rerank

    result = await rerank("query", [])
    assert result == []
    mock_client.rerank.assert_not_called()


@patch("app.services.reranker._client")
async def test_rerank_with_results(mock_client):
    from app.services.reranker import rerank

    r1 = MagicMock()
    r1.index = 0
    r1.relevance_score = 0.95
    r2 = MagicMock()
    r2.index = 1
    r2.relevance_score = 0.80
    mock_response = MagicMock()
    mock_response.results = [r1, r2]
    mock_client.rerank = AsyncMock(return_value=mock_response)

    result = await rerank("query", ["doc1", "doc2"], top_n=2)
    assert len(result) == 2
    assert result[0] == {"index": 0, "relevance_score": 0.95}
    assert result[1] == {"index": 1, "relevance_score": 0.80}
