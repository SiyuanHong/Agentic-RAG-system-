import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase


async def test_upload_document(async_client, mock_session, test_user, tmp_path):
    kb_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="KB", user_id=test_user.id)

    # First call: verify KB access, second call: unused
    mock_result_kb = MagicMock()
    mock_result_kb.scalar_one_or_none.return_value = kb
    mock_session.execute = AsyncMock(return_value=mock_result_kb)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with patch("app.api.documents._get_redis_pool") as mock_redis:
        mock_pool = AsyncMock()
        mock_redis.return_value = mock_pool
        with patch("app.api.documents.UPLOAD_DIR", tmp_path):
            resp = await async_client.post(
                f"/api/knowledge-bases/{kb_id}/documents/",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "pending"


async def test_list_documents(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="KB", user_id=test_user.id)
    doc = Document(
        id=uuid.uuid4(),
        filename="doc.pdf",
        file_path="/path",
        status=DocumentStatus.COMPLETED.value,
        kb_id=kb_id,
        user_id=test_user.id,
    )
    # First execute: verify KB, second: list docs
    mock_result_kb = MagicMock()
    mock_result_kb.scalar_one_or_none.return_value = kb
    mock_result_docs = MagicMock()
    mock_result_docs.all.return_value = [(doc, 10)]
    mock_session.execute = AsyncMock(side_effect=[mock_result_kb, mock_result_docs])

    resp = await async_client.get(f"/api/knowledge-bases/{kb_id}/documents/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["filename"] == "doc.pdf"
    assert data[0]["chunk_count"] == 10


async def test_get_document(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="doc.pdf",
        file_path="/path",
        status=DocumentStatus.COMPLETED.value,
        kb_id=kb_id,
        user_id=test_user.id,
    )
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (doc, 5)
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/knowledge-bases/{kb_id}/documents/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "doc.pdf"
    assert data["chunk_count"] == 5


async def test_delete_document(async_client, mock_session, test_user, tmp_path):
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="KB", user_id=test_user.id)

    # Create a temp file to simulate uploaded file
    fake_file = tmp_path / "test.pdf"
    fake_file.write_bytes(b"content")

    doc = Document(
        id=doc_id,
        filename="test.pdf",
        file_path=str(fake_file),
        status=DocumentStatus.COMPLETED.value,
        kb_id=kb_id,
        user_id=test_user.id,
    )
    mock_result_kb = MagicMock()
    mock_result_kb.scalar_one_or_none.return_value = kb
    mock_result_doc = MagicMock()
    mock_result_doc.scalar_one_or_none.return_value = doc
    mock_session.execute = AsyncMock(side_effect=[mock_result_kb, mock_result_doc, AsyncMock()])
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    resp = await async_client.delete(f"/api/knowledge-bases/{kb_id}/documents/{doc_id}")
    assert resp.status_code == 204


async def test_upload_to_nonexistent_kb(async_client, mock_session, test_user, tmp_path):
    kb_id = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.api.documents.UPLOAD_DIR", tmp_path):
        resp = await async_client.post(
            f"/api/knowledge-bases/{kb_id}/documents/",
            files={"file": ("test.pdf", b"fake", "application/pdf")},
        )
    assert resp.status_code == 404
