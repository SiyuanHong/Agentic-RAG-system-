import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.knowledge_bases import router as kb_router
from app.api.skills import router as skills_router
from app.services.cache import init_cache_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Redis cache index...")
    try:
        await init_cache_index()
        logger.info("Redis cache index ready")
    except Exception as e:
        logger.warning(f"Redis cache init failed (will retry on use): {e}")
    yield
    # Shutdown


app = FastAPI(title="Agentic RAG", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(skills_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
