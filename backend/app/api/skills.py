import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_current_user
from app.models.skill import Skill
from app.models.user import User

router = APIRouter(prefix="/api/skills", tags=["skills"])

MAX_SKILL_SIZE = 100 * 1024  # 100 KB


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    filename: str
    created_at: datetime | None


class SkillDetailResponse(SkillResponse):
    content: str


@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def upload_skill(
    file: UploadFile,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth

    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(
            status_code=400, detail="Only .md files are accepted"
        )

    raw = await file.read()
    if len(raw) > MAX_SKILL_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 100 KB limit")

    content = raw.decode("utf-8")
    name = file.filename.removesuffix(".md")

    skill = Skill(
        name=name,
        filename=file.filename,
        content=content,
        user_id=user.id,
    )
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        filename=skill.filename,
        created_at=skill.created_at,
    )


@router.get("/", response_model=list[SkillResponse])
async def list_skills(
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(Skill)
        .where(Skill.user_id == user.id)
        .order_by(Skill.created_at.desc())
    )
    skills = result.scalars().all()
    return [
        SkillResponse(
            id=s.id, name=s.name, filename=s.filename, created_at=s.created_at
        )
        for s in skills
    ]


@router.get("/{skill_id}", response_model=SkillDetailResponse)
async def get_skill(
    skill_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == user.id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return SkillDetailResponse(
        id=skill.id,
        name=skill.name,
        filename=skill.filename,
        content=skill.content,
        created_at=skill.created_at,
    )


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: uuid.UUID,
    auth: tuple[User, AsyncSession] = Depends(get_current_user),
):
    user, session = auth
    result = await session.execute(
        select(Skill).where(Skill.id == skill_id, Skill.user_id == user.id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await session.delete(skill)
    await session.commit()
