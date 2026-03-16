import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.security import get_current_user
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-bases"])


class KBCreate(BaseModel):
    name: str
    description: str | None = None


class KBResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    document_count: int = 0


@router.post("/", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
async def create_kb(
    body: KBCreate,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    kb = KnowledgeBase(name=body.name, description=body.description, user_id=user.id)
    session.add(kb)
    await session.commit()
    await session.refresh(kb)
    return KBResponse(id=kb.id, name=kb.name, description=kb.description)


@router.get("/", response_model=list[KBResponse])
async def list_kbs(
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    stmt = (
        select(
            KnowledgeBase,
            func.count(Document.id).label("doc_count"),
        )
        .outerjoin(Document, Document.kb_id == KnowledgeBase.id)
        .where(KnowledgeBase.user_id == user.id)
        .group_by(KnowledgeBase.id)
    )
    results = await session.execute(stmt)
    return [
        KBResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            document_count=doc_count,
        )
        for kb, doc_count in results.all()
    ]


@router.get("/{kb_id}", response_model=KBResponse)
async def get_kb(
    kb_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    stmt = (
        select(
            KnowledgeBase,
            func.count(Document.id).label("doc_count"),
        )
        .outerjoin(Document, Document.kb_id == KnowledgeBase.id)
        .where(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id)
        .group_by(KnowledgeBase.id)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    kb, doc_count = row
    return KBResponse(
        id=kb.id, name=kb.name, description=kb.description, document_count=doc_count
    )


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb(
    kb_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await session.delete(kb)
    await session.commit()
