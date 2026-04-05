from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


class MEMORY_TYPE(str, Enum):
    PREFERENCE = "preference"
    GOAL = "goal"
    ACHIEVEMENT = "achievement"
    LEARNING = "learning"
    EMOTIONAL = "emotional"


class BaseModel(SQLModel, table=False):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)


class CheckList(BaseModel, table=True):
    __tablename__ = "checklists"
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    tasks: List["Task"] = Relationship(back_populates="checklist")
    items: List["CheckListItem"] = Relationship(back_populates="checklist")


class CheckListItem(BaseModel, table=True):
    __tablename__ = "checklist_items"
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    checklist_id: int = Field(foreign_key="checklists.id")
    checklist: CheckList = Relationship(back_populates="items")
    is_checked: bool = Field(default=False)


class Note(BaseModel, table=True):
    __tablename__ = "notes"
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    content: str = Field(index=True)


class Memory(BaseModel, table=True):
    __tablename__ = "memories"
    key: str = Field(index=True)
    content: str = Field(default=None)
    memory_type: MEMORY_TYPE = Field(default=MEMORY_TYPE.PREFERENCE)


class Task(BaseModel, table=True):
    __tablename__ = "tasks"
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    deadline: Optional[datetime] = Field(default=None)
    checklist_id: Optional[int] = Field(foreign_key="checklists.id")
    checklist: Optional[CheckList] = Relationship(back_populates="tasks")


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
    tool_calls: Optional[List[ToolCall]] = Relationship(back_populates="message")
    input_tokens: Optional[int] = Field(default=0)
    output_tokens: Optional[int] = Field(default=0)
    model_name: Optional[str] = Field(default=None)


class ChatSession(BaseModel, table=True):
    __tablename__ = "chat_sessions"
    name: Optional[str] = Field(index=True)
    summary: Optional[str] = Field(default=None)
    messages: Optional[List[Message]] = Relationship(back_populates="chat_session")
