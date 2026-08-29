from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, Relationship, SQLModel


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    # Retained for compatibility with databases created by earlier releases.
    TOOL = "tool"


class MEMORY_TYPE(StrEnum):
    PREFERENCE = "preference"
    GOAL = "goal"
    ACHIEVEMENT = "achievement"
    LEARNING = "learning"
    EMOTIONAL = "emotional"


class BaseModel(SQLModel, table=False):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None)


class CheckList(BaseModel, table=True):
    __tablename__ = "checklists"
    title: str = Field(index=True)
    description: str | None = Field(default=None)
    tasks: list["Task"] = Relationship(back_populates="checklist")
    items: list["CheckListItem"] = Relationship(back_populates="checklist")


class CheckListItem(BaseModel, table=True):
    __tablename__ = "checklist_items"
    title: str = Field(index=True)
    description: str | None = Field(default=None)
    checklist_id: int = Field(foreign_key="checklists.id")
    checklist: CheckList = Relationship(back_populates="items")
    is_checked: bool = Field(default=False)


class Note(BaseModel, table=True):
    __tablename__ = "notes"
    title: str = Field(index=True)
    description: str | None = Field(default=None)
    content: str = Field(index=True)


class Memory(BaseModel, table=True):
    __tablename__ = "memories"
    key: str = Field(index=True)
    content: str = Field(default=None)
    memory_type: MEMORY_TYPE = Field(default=MEMORY_TYPE.PREFERENCE)


class Task(BaseModel, table=True):
    __tablename__ = "tasks"
    title: str = Field(index=True)
    description: str | None = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    deadline: datetime | None = Field(default=None)
    checklist_id: int | None = Field(foreign_key="checklists.id")
    checklist: CheckList | None = Relationship(back_populates="tasks")


class ToolCall(BaseModel, table=True):
    __tablename__ = "tool_calls"
    tool_name: str = Field(index=True)
    payload: str = Field(default=None)
    response: str = Field(default=None)
    message_id: int = Field(foreign_key="messages.id")
    message: "Message" = Relationship(back_populates="tool_calls")


class Message(BaseModel, table=True):
    __tablename__ = "messages"
    content: str = Field(index=True)
    role: MessageRole = Field(default=MessageRole.USER)
    chat_session_id: int = Field(foreign_key="chat_sessions.id")
    chat_session: "ChatSession" = Relationship(back_populates="messages")
    tool_calls: list[ToolCall] | None = Relationship(back_populates="message")
    input_tokens: int | None = Field(default=0)
    output_tokens: int | None = Field(default=0)
    model_name: str | None = Field(default=None)


class ChatSession(BaseModel, table=True):
    __tablename__ = "chat_sessions"
    name: str | None = Field(index=True)
    summary: str | None = Field(default=None)
    summary_message_count: int = Field(default=0)
    messages: list[Message] | None = Relationship(back_populates="chat_session")
