import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.models.skill import Skill


async def test_upload_skill(async_client, mock_session, test_user):
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    resp = await async_client.post(
        "/api/skills/",
        files={"file": ("legal_expert.md", b"# Legal Expert\nYou are a legal expert.", "text/markdown")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "legal_expert"
    assert data["filename"] == "legal_expert.md"


async def test_upload_skill_non_md(async_client, mock_session):
    resp = await async_client.post(
        "/api/skills/",
        files={"file": ("skill.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 400
    assert "Only .md files" in resp.json()["detail"]


async def test_upload_skill_too_large(async_client, mock_session):
    large_content = b"x" * (100 * 1024 + 1)
    resp = await async_client.post(
        "/api/skills/",
        files={"file": ("big.md", large_content, "text/markdown")},
    )
    assert resp.status_code == 400
    assert "100 KB" in resp.json()["detail"]


async def test_list_skills(async_client, mock_session, test_user):
    skill = Skill(
        id=uuid.uuid4(),
        name="analyst",
        filename="analyst.md",
        content="You are an analyst.",
        user_id=test_user.id,
        created_at=datetime(2024, 1, 1),
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [skill]
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get("/api/skills/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "analyst"


async def test_get_skill(async_client, mock_session, test_user):
    skill_id = uuid.uuid4()
    skill = Skill(
        id=skill_id,
        name="analyst",
        filename="analyst.md",
        content="You are an analyst.",
        user_id=test_user.id,
        created_at=datetime(2024, 1, 1),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = skill
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/skills/{skill_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "You are an analyst."
    assert data["name"] == "analyst"


async def test_delete_skill(async_client, mock_session, test_user):
    skill_id = uuid.uuid4()
    skill = Skill(
        id=skill_id,
        name="analyst",
        filename="analyst.md",
        content="content",
        user_id=test_user.id,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = skill
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    resp = await async_client.delete(f"/api/skills/{skill_id}")
    assert resp.status_code == 204


async def test_get_skill_not_found(async_client, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await async_client.get(f"/api/skills/{uuid.uuid4()}")
    assert resp.status_code == 404
