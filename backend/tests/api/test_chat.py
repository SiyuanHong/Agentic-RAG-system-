import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message, MessageRole


async def test_create_conversation(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    kb = KnowledgeBase(id=kb_id, name="KB", user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = kb
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    resp = await async_client.post("/api/chat/conversations", json={"kb_id": str(kb_id)})
    assert resp.status_code == 201
    data = resp.json()
    assert data["kb_id"] == str(kb_id)


async def test_list_conversations(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    conv = Conversation(id=uuid.uuid4(), title="Test conv", kb_id=kb_id, user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [conv]
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get("/api/chat/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test conv"


async def test_list_conversations_filter_kb(async_client, mock_session, test_user):
    kb_id = uuid.uuid4()
    conv = Conversation(id=uuid.uuid4(), title="Filtered", kb_id=kb_id, user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [conv]
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/chat/conversations?kb_id={kb_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


async def test_delete_conversation(async_client, mock_session, test_user):
    conv_id = uuid.uuid4()
    conv = Conversation(id=conv_id, kb_id=uuid.uuid4(), user_id=test_user.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = conv
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    resp = await async_client.delete(f"/api/chat/conversations/{conv_id}")
    assert resp.status_code == 204


async def test_get_messages(async_client, mock_session, test_user):
    conv_id = uuid.uuid4()
    conv = Conversation(id=conv_id, kb_id=uuid.uuid4(), user_id=test_user.id)
    msg = Message(
        id=uuid.uuid4(),
        role=MessageRole.USER.value,
        content="Hello",
        conversation_id=conv_id,
        user_id=test_user.id,
    )

    # First execute: verify conv ownership, second: get messages
    mock_result_conv = MagicMock()
    mock_result_conv.scalar_one_or_none.return_value = conv
    mock_result_msgs = MagicMock()
    mock_result_msgs.scalars.return_value.all.return_value = [msg]
    mock_session.execute = AsyncMock(side_effect=[mock_result_conv, mock_result_msgs])

    resp = await async_client.get(f"/api/chat/conversations/{conv_id}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello"
    assert data[0]["role"] == "user"


async def test_create_conversation_invalid_kb(async_client, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.post("/api/chat/conversations", json={"kb_id": str(uuid.uuid4())})
    assert resp.status_code == 404
