from unittest.mock import AsyncMock, MagicMock, patch


@patch("app.services.embedding._client")
async def test_embed_texts_empty(mock_client):
    from app.services.embedding import embed_texts

    result = await embed_texts([])
    assert result == []
    mock_client.embeddings.create.assert_not_called()


@patch("app.services.embedding._client")
async def test_embed_texts_single_batch(mock_client):
    from app.services.embedding import embed_texts

    mock_item = MagicMock()
    mock_item.embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [mock_item]
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    result = await embed_texts(["hello"])
    assert result == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once()


@patch("app.services.embedding._client")
async def test_embed_texts_multiple_batches(mock_client):
    from app.services.embedding import embed_texts

    def make_response(n):
        items = []
        for _ in range(n):
            item = MagicMock()
            item.embedding = [0.1]
            items.append(item)
        resp = MagicMock()
        resp.data = items
        return resp

    # 20 texts, batch size 15 → 2 calls
    mock_client.embeddings.create = AsyncMock(
        side_effect=[make_response(15), make_response(5)]
    )
    result = await embed_texts(["text"] * 20)
    assert len(result) == 20
    assert mock_client.embeddings.create.call_count == 2
