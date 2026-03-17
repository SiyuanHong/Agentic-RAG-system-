import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.knowledge_base import KnowledgeBase


async def test_create_kb(async_client, mock_session):
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    resp = await async_client.post(
        "/api/knowledge-bases/",
        json={"name": "Test KB", "description": "A test knowledge base"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test KB"
    assert data["description"] == "A test knowledge base"
    assert "id" in data


async def test_list_kbs_empty(async_client, mock_session):
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get("/api/knowledge-bases/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_kbs_with_data(async_client, mock_session, test_user):
    kb = KnowledgeBase(
        id=uuid.uuid4(), name="My KB", description="desc", user_id=test_user.id
    )
    mock_result = MagicMock()
    mock_result.all.return_value = [(kb, 3)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get("/api/knowledge-bases/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "My KB"
    assert data[0]["document_count"] == 3


async def test_get_kb(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="Found KB", description=None, user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (kb, 5)
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/knowledge-bases/{kb_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Found KB"
    assert data["document_count"] == 5


async def test_get_kb_not_found(async_client, mock_session):
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/knowledge-bases/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_delete_kb(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="Delete Me", user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = kb
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    resp = await async_client.delete(f"/api/knowledge-bases/{kb_id}")
    assert resp.status_code == 204


async def test_delete_kb_not_found(async_client, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.delete(f"/api/knowledge-bases/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_unauthenticated():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    # No auth override — should get 401
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/knowledge-bases/")
        assert resp.status_code == 401
