import logging
import uuid
from pathlib import Path

import arq
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.core.security import get_current_user
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

router = APIRouter(
    prefix="/api/knowledge-bases/{kb_id}/documents", tags=["documents"]
)

UPLOAD_DIR = Path("uploads")


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    error_message: str | None = None
    chunk_count: int = 0


async def _get_redis_pool() -> arq.ArqRedis:
    return await arq.create_pool(arq.connections.RedisSettings.from_dsn(settings.REDIS_URL))


async def _verify_kb_access(
    kb_id: uuid.UUID, user: User, session: AsyncSession
) -> KnowledgeBase:
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    await _verify_kb_access(kb_id, user, session)

    # Save file
    file_dir = UPLOAD_DIR / str(kb_id)
    file_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix
    file_id = uuid.uuid4()
    file_path = file_dir / f"{file_id}{ext}"

    content = await file.read()
    file_path.write_bytes(content)

    # Create document row
    doc = Document(
        id=file_id,
        filename=file.filename or "unknown",
        file_path=str(file_path),
        status=DocumentStatus.PENDING.value,
        kb_id=kb_id,
        user_id=user.id,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # Enqueue ingestion job
    redis = None
    try:
        redis = await _get_redis_pool()
        await redis.enqueue_job("process_document", str(doc.id))
    except Exception as e:
        logger.warning(f"Failed to enqueue ingestion job: {e}")
    finally:
        if redis:
            await redis.aclose()

    return DocumentResponse(id=doc.id, filename=doc.filename, status=doc.status)


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    await _verify_kb_access(kb_id, user, session)

    stmt = (
        select(Document, func.count(Chunk.id).label("chunk_count"))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.kb_id == kb_id, Document.user_id == user.id)
        .group_by(Document.id)
    )
    results = await session.execute(stmt)
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=chunk_count,
        )
        for doc, chunk_count in results.all()
    ]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    stmt = (
        select(Document, func.count(Chunk.id).label("chunk_count"))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(
            Document.id == doc_id,
            Document.kb_id == kb_id,
            Document.user_id == user.id,
        )
        .group_by(Document.id)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    doc, chunk_count = row
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
    )


@router.get("/{doc_id}/file")
async def get_document_file(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.kb_id == kb_id,
            Document.user_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine media type from extension
    suffix = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=doc.filename,
        media_type=media_type,
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    await _verify_kb_access(kb_id, user, session)

    result = await session.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.kb_id == kb_id,
            Document.user_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete associated chunks first
    await session.execute(
        sa_delete(Chunk).where(Chunk.document_id == doc_id)
    )

    # Delete the uploaded file
    try:
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass  # File cleanup is best-effort

    await session.delete(doc)
    await session.commit()
