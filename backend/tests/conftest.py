import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.models.user import User


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        hashed_password="hashed",
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.add_all = MagicMock()
    return session


@pytest.fixture
def test_app(test_user: User, mock_session: AsyncMock) -> FastAPI:
    from app.main import app

    async def override_auth():
        return test_user, mock_session

    app.dependency_overrides[get_current_user] = override_auth
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
