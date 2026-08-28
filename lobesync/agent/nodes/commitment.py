import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage
from sqlmodel import Session

from lobesync.agent.models import get_chat_model
from lobesync.agent.state import AgentState
from lobesync.db.database import get_engine
from lobesync.db.models import Message, MessageRole
from lobesync.db.repos.chat_repo import (
    create_message,
    create_tool_call,
    get_chat_session_by_id,
    get_messages_by_session,
)

logger = logging.getLogger(__name__)

_SUMMARY_EVERY = 5
_KEEP_LAST = 5


def _generate_summary(
    existing_summary: str | None, messages_to_compress: Sequence[Message]
) -> str:
    formatted = "\n".join(
        [f"{msg.role.value.upper()}: {msg.content}" for msg in messages_to_compress]
    )

    if existing_summary:
        prompt = f"Previous summary:\n{existing_summary}\n\nNew exchanges to incorporate:\n{formatted}\n\nUpdate the summary concisely."
    else:
        prompt = f"Summarize this conversation concisely:\n{formatted}"

    model = get_chat_model(max_tokens=512)
    response = model.invoke([HumanMessage(content=prompt)])
    return str(response.content)


def _update_session_name(session: Session, chat_session_id: int, first_user_message: str) -> None:
    from lobesync.db.models import ChatSession

    chat_session = session.get(ChatSession, chat_session_id)
    if chat_session and chat_session.name == "Lobesync":
        chat_session.name = first_user_message[:40].strip()
        session.add(chat_session)


def _update_summary(chat_session_id: int) -> None:
    """Summarize only messages that have not already been summarized.

    The model call deliberately happens outside a database transaction so a
    slow provider cannot hold a write lock on the user's data.
    """
    with Session(get_engine()) as session:
        chat_session = get_chat_session_by_id(session, chat_session_id)
        messages = get_messages_by_session(session, chat_session_id) or []
        if not chat_session:
            return

        total = len(messages)
        end = total - _KEEP_LAST
        start = chat_session.summary_message_count
        if end <= start or total % _SUMMARY_EVERY != 0:
            return

        existing_summary = chat_session.summary
        messages_to_compress = messages[start:end]

    logger.info("Regenerating summary for %s message(s)", len(messages_to_compress))
    new_summary = _generate_summary(existing_summary, messages_to_compress)

    with Session(get_engine()) as session:
        chat_session = get_chat_session_by_id(session, chat_session_id)
        if not chat_session:
            return
        chat_session.summary = new_summary
        chat_session.summary_message_count = end
        chat_session.updated_at = datetime.now(UTC)
        session.add(chat_session)
        session.commit()


def commitment_node(state: AgentState) -> dict:
    """
    Persists the conversation turn, tool calls, and manages incremental summary.
    Always runs last — owns all DB writes for the turn.
    """
    chat_session_id = state["chat_session_id"]
    user_query = state["user_query"]
    final_response = state["final_response"] or "No response was generated."
    input_tokens = state.get("input_tokens", 0)
    output_tokens = state.get("output_tokens", 0)
    model_name = state.get("model_name")
    execution_results = state.get("execution_results") or []

    with Session(get_engine()) as session:
        create_message(session, chat_session_id, user_query, MessageRole.USER)
        assistant_msg = create_message(
            session,
            chat_session_id,
            final_response,
            MessageRole.AGENT,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name=model_name,
        )
        session.flush()

        # Save tool calls linked to the assistant message
        if execution_results and assistant_msg:
            if assistant_msg.id is None:
                raise RuntimeError("Persisted assistant message is missing an id")

            def _safe_json(obj) -> str:
                return json.dumps(
                    obj, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o)
                )

            for r in execution_results:
                payload = _safe_json(r.get("args", {}))
                response = (
                    _safe_json(r["result"])
                    if r.get("result") is not None
                    else (r.get("error") or "")
                )
                create_tool_call(
                    session,
                    message_id=assistant_msg.id,
                    tool_name=r["tool"],
                    payload=payload,
                    response=response,
                )

        all_messages = get_messages_by_session(session, chat_session_id) or []
        total = len(all_messages)

        if total <= 2:
            _update_session_name(session, chat_session_id, user_query)

        session.commit()

    _update_summary(chat_session_id)

    logger.info(f"Commitment: saved turn for session {chat_session_id} ({total} total messages)")
    return {}
