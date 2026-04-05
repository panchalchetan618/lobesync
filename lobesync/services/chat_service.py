from sqlmodel import Session
import logging

from lobesync.db.repos.chat_repo import (
    create_chat_session,
    get_chat_session_by_id,
    get_all_chat_sessions,
    update_chat_session_summary,
    create_message,
    get_messages_by_session,
    create_tool_call,
    get_tool_calls_by_message,
)
from lobesync.db.models import MessageRole
from lobesync.exceptions.chat_exceptions import ChatSessionNotFoundError

logger = logging.getLogger(__name__)


def create_chat_session_service(session: Session, name: str | None = None):
    """
    Creates a new chat session.

    Args:
        session (Session): Active database session.
        name (str | None): Optional display name for the session.

    Returns:
        ChatSession | None: The created session if successful, otherwise None.
    """
    return create_chat_session(session, name)


def get_all_chat_sessions_service(session: Session):
    """
    Retrieves all chat sessions.

    Args:
        session (Session): Active database session.

    Returns:
        List[ChatSession] | None: All sessions if any exist, otherwise None.
    """
    return get_all_chat_sessions(session)


def get_chat_session_service(session: Session, chat_session_id: int):
    """
    Retrieves a chat session by ID. Raises if not found.

    Args:
        session (Session): Active database session.
        chat_session_id (int): Primary key of the chat session.

    Returns:
        ChatSession: The chat session.

    Raises:
        ChatSessionNotFoundError: If no session exists with the given ID.
    """
    chat_session = get_chat_session_by_id(session, chat_session_id)
    if not chat_session:
        raise ChatSessionNotFoundError(f"Chat session {chat_session_id} not found")
    return chat_session


def update_chat_session_summary_service(session: Session, chat_session_id: int, summary: str):
    """
    Updates the summary of a chat session. Raises if not found.

    Args:
        session (Session): Active database session.
        chat_session_id (int): Primary key of the chat session.
        summary (str): New summary content.

    Returns:
        ChatSession: The updated session.

    Raises:
        ChatSessionNotFoundError: If no session exists with the given ID.
    """
    chat_session = get_chat_session_by_id(session, chat_session_id)
    if not chat_session:
        raise ChatSessionNotFoundError(f"Chat session {chat_session_id} not found")
    return update_chat_session_summary(session, chat_session_id, summary)


def add_message_service(
    session: Session,
    chat_session_id: int,
    content: str,
    role: MessageRole,
    input_tokens: int = 0,
    output_tokens: int = 0,
    model_name: str | None = None,
):
    """
    Adds a message to a chat session. Raises if session not found.

    Args:
        session (Session): Active database session.
        chat_session_id (int): ID of the parent chat session.
        content (str): Message body.
        role (MessageRole): Role of the message author.
        input_tokens (int): Input token count, if tracked.
        output_tokens (int): Output token count, if tracked.
        model_name (str | None): Model identifier, if applicable.

    Returns:
        Message | None: The created message if successful, otherwise None.

    Raises:
        ChatSessionNotFoundError: If the parent session does not exist.
    """
    chat_session = get_chat_session_by_id(session, chat_session_id)
    if not chat_session:
        raise ChatSessionNotFoundError(f"Chat session {chat_session_id} not found")
    return create_message(session, chat_session_id, content, role, input_tokens, output_tokens, model_name)


def get_messages_service(session: Session, chat_session_id: int):
    """
    Retrieves all messages for a session ordered by creation time. Raises if session not found.

    Args:
        session (Session): Active database session.
        chat_session_id (int): ID of the chat session.

    Returns:
        List[Message] | None: Messages in order if any exist, otherwise None.

    Raises:
        ChatSessionNotFoundError: If the session does not exist.
    """
    chat_session = get_chat_session_by_id(session, chat_session_id)
    if not chat_session:
        raise ChatSessionNotFoundError(f"Chat session {chat_session_id} not found")
    return get_messages_by_session(session, chat_session_id)


def record_tool_call_service(session: Session, message_id: int, tool_name: str, payload: str, response: str):
    """
    Records a tool invocation linked to a message.

    Args:
        session (Session): Active database session.
        message_id (int): ID of the parent message.
        tool_name (str): Name of the tool called.
        payload (str): Serialized arguments sent to the tool.
        response (str): Serialized tool response.

    Returns:
        ToolCall | None: The created tool call record if successful, otherwise None.
    """
    return create_tool_call(session, message_id, tool_name, payload, response)


def get_tool_calls_service(session: Session, message_id: int):
    """
    Retrieves all tool calls for a given message.

    Args:
        session (Session): Active database session.
        message_id (int): ID of the message.

    Returns:
        List[ToolCall] | None: Tool calls for that message if any, otherwise None.
    """
    return get_tool_calls_by_message(session, message_id)
