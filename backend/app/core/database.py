from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, text

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def set_rls_context(session: AsyncSession, user_id: str) -> None:
    # SET doesn't support parameterized queries — use string literal.
    # user_id is always a validated UUID from our JWT, so this is safe.
    safe_uid = str(user_id).replace("'", "")
    await session.execute(text(f"SET app.current_user_id = '{safe_uid}'"))
