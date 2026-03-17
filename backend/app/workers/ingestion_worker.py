import asyncio
import logging
import sys

from arq import func
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.cache import invalidate_cache_for_kb
from app.services.ingestion import process_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Python 3.14 removed auto-creation of event loops in get_event_loop().
# arq's Worker.__init__ calls get_event_loop(), so we ensure one exists.
if sys.version_info >= (3, 14):
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


async def run_process_document(ctx: dict, document_id: str) -> None:
    from sqlmodel import select
    from app.models.document import Document

    async with async_session_factory() as session:
        await process_document(document_id, session)
        # Invalidate cache for the KB after successful ingestion
        result = await session.execute(
            select(Document.kb_id).where(Document.id == document_id)
        )
        row = result.scalar_one_or_none()
        if row:
            try:
                await invalidate_cache_for_kb(str(row))
            except Exception:
                pass


async def startup(ctx: dict) -> None:
    logger.info("Ingestion worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("Ingestion worker shutting down")


class WorkerSettings:
    functions = [func(run_process_document, name="process_document")]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 600  # 10 min per document
