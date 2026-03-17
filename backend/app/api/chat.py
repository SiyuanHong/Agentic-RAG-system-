import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sa_delete
from sqlmodel import select

from app.agent.graph import run_agent
from app.core.security import get_current_user
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.message import Message, MessageRole
from app.models.skill import Skill
from app.models.user import User
from app.core.database import async_session_factory, set_rls_context
from app.services.cache import cache_lookup, cache_store
from app.services.embedding import embed_texts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ConversationCreate(BaseModel):
    kb_id: uuid.UUID


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    kb_id: uuid.UUID


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    sources: list[dict] | None = None


class ChatRequest(BaseModel):
    query: str
    skill_id: uuid.UUID | None = None


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    # Verify KB access
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == body.kb_id, KnowledgeBase.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    conv = Conversation(kb_id=body.kb_id, user_id=user.id)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return ConversationResponse(id=conv.id, title=conv.title, kb_id=conv.kb_id)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    kb_id: uuid.UUID | None = None,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if kb_id:
        stmt = stmt.where(Conversation.kb_id == kb_id)
    stmt = stmt.order_by(Conversation.created_at.desc())
    result = await session.execute(stmt)
    convs = result.scalars().all()
    return [
        ConversationResponse(id=c.id, title=c.title, kb_id=c.kb_id) for c in convs
    ]


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete associated messages first (bulk DELETE to avoid ORM reordering)
    await session.execute(
        sa_delete(Message).where(Message.conversation_id == conversation_id)
    )
    await session.delete(conv)
    await session.commit()


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    conversation_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    # Verify conversation ownership
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        MessageResponse(id=m.id, role=m.role, content=m.content, sources=m.sources)
        for m in messages
    ]


@router.post("/conversations/{conversation_id}/stream")
async def stream_chat(
    conversation_id: uuid.UUID,
    body: ChatRequest,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth

    # Verify conversation and get KB
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_msg = Message(
        role=MessageRole.USER.value,
        content=body.query,
        conversation_id=conversation_id,
        user_id=user.id,
    )
    session.add(user_msg)
    await session.commit()

    kb_id = str(conv.kb_id)
    user_id = str(user.id)

    # Resolve skill if provided
    skill_content = ""
    if body.skill_id:
        result = await session.execute(
            select(Skill).where(
                Skill.id == body.skill_id, Skill.user_id == user.id
            )
        )
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill_content = skill.content

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Check semantic cache (skip when skill is selected to avoid cross-skill pollution)
            query_embedding = None
            cached = None
            if not skill_content:
                try:
                    query_embedding = (await embed_texts([body.query]))[0]
                    cached = await cache_lookup(query_embedding, kb_id)
                except Exception:
                    query_embedding = None
                    cached = None

            if cached:
                yield f"data: {json.dumps({'event': 'cache_hit', 'data': 'Using cached answer'})}\n\n"
                yield f"data: {json.dumps({'event': 'token', 'data': cached})}\n\n"
                # Save assistant message
                async with async_session_factory() as s:
                    await set_rls_context(s, user_id)
                    assistant_msg = Message(
                        role=MessageRole.ASSISTANT.value,
                        content=cached,
                        conversation_id=conversation_id,
                        user_id=user.id,
                    )
                    s.add(assistant_msg)
                    await s.commit()
                yield f"data: {json.dumps({'event': 'done'})}\n\n"
                return

            # Run agent pipeline
            final_answer = ""
            sources_list: list[dict] | None = None
            async for event in run_agent(body.query, kb_id, user_id, skill_content):
                if event["event"] == "answer":
                    final_answer = event["data"]
                elif event["event"] == "sources":
                    try:
                        sources_list = json.loads(event["data"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                yield f"data: {json.dumps(event)}\n\n"

            # Save assistant message
            async with async_session_factory() as s:
                await set_rls_context(s, user_id)
                assistant_msg = Message(
                    role=MessageRole.ASSISTANT.value,
                    content=final_answer,
                    sources=sources_list,
                    conversation_id=conversation_id,
                    user_id=user.id,
                )
                s.add(assistant_msg)
                # Update conversation title if first message
                result = await s.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                c = result.scalar_one_or_none()
                if c and not c.title:
                    c.title = body.query[:100]
                    s.add(c)
                await s.commit()

            # Store in cache
            if query_embedding and final_answer:
                try:
                    await cache_store(query_embedding, kb_id, final_answer)
                except Exception:
                    pass  # Cache store failure is non-critical

            yield f"data: {json.dumps({'event': 'done'})}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled by client for conversation %s", conversation_id)
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
