import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, JSON, func
from sqlmodel import Field, SQLModel


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    content: str
    chunk_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)),
    )
    document_id: uuid.UUID = Field(foreign_key="documents.id", index=True)
    kb_id: uuid.UUID = Field(foreign_key="knowledge_bases.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
