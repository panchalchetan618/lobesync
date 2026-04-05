from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError
from lobesync.db.models import ChatSession, Message, MessageRole, ToolCall
from typing import List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# --- ChatSession ---


def create_chat_session(
    session: Session, name: str | None = None
) -> ChatSession | None:
    """
    Creates and persists a new chat session.

    Args:
        session (Session): Active database session used for persistence.
        name (str | None): Optional display name for the session.

    Returns:
        ChatSession | None: The created session if successful, otherwise None.
    """
    try:
        chat_session = ChatSession(name=name)
        session.add(chat_session)
        session.flush()
        session.refresh(chat_session)
        return chat_session
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_chat_session] Failed. Error: {e}")
        return None


def get_chat_session_by_id(
    session: Session, chat_session_id: int
) -> ChatSession | None:
    """
    Retrieves a chat session by primary key.

    Args:
        session (Session): Active database session used for querying.
        chat_session_id (int): Primary key of the chat session.

    Returns:
        ChatSession | None: The session if found, otherwise None.
    """
    try:
        return session.get(ChatSession, chat_session_id)
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_chat_session_by_id] Failed. Error: {e}")
        return None


def get_all_chat_sessions(session: Session) -> List[ChatSession] | None:
    """
    Retrieves all chat sessions.

    Args:
        session (Session): Active database session used for querying.

    Returns:
        List[ChatSession] | None: All sessions if any exist, otherwise None.
    """
    try:
        sessions = session.exec(select(ChatSession)).all()
        return sessions or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_all_chat_sessions] Failed. Error: {e}")
        return None


def update_chat_session_summary(
    session: Session, chat_session_id: int, summary: str
) -> ChatSession | None:
    """
    Updates the summary text and timestamp for a chat session.

    Args:
        session (Session): Active database session used for persistence.
        chat_session_id (int): Primary key of the chat session.
        summary (str): New summary content.

    Returns:
        ChatSession | None: The updated session, or None if not found or on failure.
    """
    try:
        chat_session = session.get(ChatSession, chat_session_id)
        if not chat_session:
            return None
        chat_session.summary = summary
        chat_session.updated_at = datetime.now()
        session.add(chat_session)
        session.flush()
        session.refresh(chat_session)
        return chat_session
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) update_chat_session_summary] Failed. Error: {e}")
        return None


def create_message(
    session: Session,
    chat_session_id: int,
    content: str,
    role: MessageRole,
    input_tokens: int = 0,
    output_tokens: int = 0,
    model_name: str | None = None,
) -> Message | None:
    """
    Creates and persists a message within a chat session.

    Args:
        session (Session): Active database session used for persistence.
        chat_session_id (int): ID of the parent chat session.
        content (str): Message body text.
        role (MessageRole): Role of the message author (e.g. user, assistant).
        input_tokens (int): Token count for input context, if tracked.
        output_tokens (int): Token count for model output, if tracked.
        model_name (str | None): Optional model identifier used for the message.

    Returns:
        Message | None: The created message if successful, otherwise None.
    """
    try:
        message = Message(
            chat_session_id=chat_session_id,
            content=content,
            role=role,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
        )
        session.add(message)
        session.flush()
        session.refresh(message)
        return message
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_message] Failed. Error: {e}")
        return None


def get_messages_by_session(
    session: Session, chat_session_id: int
) -> List[Message] | None:
    """
    Retrieves all messages for a session, ordered by creation time (oldest first).

    Args:
        session (Session): Active database session used for querying.
        chat_session_id (int): ID of the chat session.

    Returns:
        List[Message] | None: Messages in that session if any, otherwise None.
    """
    try:
        messages = session.exec(
            select(Message)
            .where(Message.chat_session_id == chat_session_id)
            .order_by(Message.created_at)
        ).all()
        return messages or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_messages_by_session] Failed. Error: {e}")
        return None


# --- ToolCall ---


def create_tool_call(
    session: Session, message_id: int, tool_name: str, payload: str, response: str
) -> ToolCall | None:
    """
    Creates and persists a tool invocation record linked to a message.

    Args:
        session (Session): Active database session used for persistence.
        message_id (int): ID of the parent message.
        tool_name (str): Name of the tool that was called.
        payload (str): Serialized request or arguments sent to the tool.
        response (str): Serialized tool response.

    Returns:
        ToolCall | None: The created ToolCall if successful, otherwise None.
    """
    try:
        tool_call = ToolCall(
            message_id=message_id,
            tool_name=tool_name,
            payload=payload,
            response=response,
        )
        session.add(tool_call)
        session.flush()
        session.refresh(tool_call)
        return tool_call
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) create_tool_call] Failed. Error: {e}")
        return None


def get_tool_calls_by_message(
    session: Session, message_id: int
) -> List[ToolCall] | None:
    """
    Retrieves all tool calls associated with a message.

    Args:
        session (Session): Active database session used for querying.
        message_id (int): ID of the message.

    Returns:
        List[ToolCall] | None: Tool calls for that message if any, otherwise None.
    """
    try:
        tool_calls = session.exec(
            select(ToolCall).where(ToolCall.message_id == message_id)
        ).all()
        return tool_calls or None
    except SQLAlchemyError as e:
        logger.error(f"[(REPO) get_tool_calls_by_message] Failed. Error: {e}")
        return None
