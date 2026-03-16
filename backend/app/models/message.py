import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String, func
from sqlmodel import Field, SQLModel


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    role: str = Field(sa_column=Column(String))
    content: str
    sources: list[dict] | None = Field(default=None, sa_column=Column(JSON))
    conversation_id: uuid.UUID = Field(foreign_key="conversations.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
