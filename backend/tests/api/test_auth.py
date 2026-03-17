import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.main import app
from app.models.user import User


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    return session


@pytest.fixture
def auth_app(mock_session):
    async def override_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_session
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(auth_app):
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_register_success(client, mock_session):
    # No existing user
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    new_user = User(
        id=uuid.uuid4(), email="new@example.com", hashed_password="hashed"
    )
    mock_session.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", new_user.id))

    resp = await client.post("/auth/register", json={"email": "new@example.com", "password": "pass123"})
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client, mock_session):
    existing_user = User(
        id=uuid.uuid4(), email="dup@example.com", hashed_password="hashed"
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await client.post("/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    assert resp.status_code == 409


async def test_login_success(client, mock_session):
    from app.core.security import hash_password

    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        hashed_password=hash_password("correct"),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await client.post("/auth/login", json={"email": "login@example.com", "password": "correct"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


async def test_login_wrong_password(client, mock_session):
    from app.core.security import hash_password

    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        hashed_password=hash_password("correct"),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await client.post("/auth/login", json={"email": "login@example.com", "password": "wrong"})
    assert resp.status_code == 401


async def test_login_nonexistent_email(client, mock_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "pass"})
    assert resp.status_code == 401
