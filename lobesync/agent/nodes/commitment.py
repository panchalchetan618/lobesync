import anthropic
import json
import logging
from datetime import datetime
from sqlmodel import Session

from lobesync.config import config
from lobesync.db.database import engine
from lobesync.db.models import MessageRole
from lobesync.db.repos.chat_repo import (
    create_message,
    create_tool_call,
    get_messages_by_session,
    update_chat_session_summary,
    get_chat_session_by_id,
)
from lobesync.agent.state import AgentState

logger = logging.getLogger(__name__)

_SUMMARY_EVERY = 5
_KEEP_LAST = 5


def _generate_summary(existing_summary: str | None, messages_to_compress: list) -> str:
    formatted = "\n".join([
        f"{msg.role.value.upper()}: {msg.content}"
        for msg in messages_to_compress
    ])

    if existing_summary:
        prompt = f"Previous summary:\n{existing_summary}\n\nNew exchanges to incorporate:\n{formatted}\n\nUpdate the summary concisely."
    else:
        prompt = f"Summarize this conversation concisely:\n{formatted}"

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _update_session_name(session: Session, chat_session_id: int, first_user_message: str):
    from lobesync.db.models import ChatSession
    chat_session = session.get(ChatSession, chat_session_id)
    if chat_session and chat_session.name == "Lobesync":
        chat_session.name = first_user_message[:40].strip()
        session.add(chat_session)


def commitment_node(state: AgentState) -> dict:
    """
    Persists the conversation turn, tool calls, and manages incremental summary.
    Always runs last — owns all DB writes for the turn.
    """
    chat_session_id = state["chat_session_id"]
    user_query = state["user_query"]
    final_response = state["final_response"]
    input_tokens = state.get("input_tokens", 0)
    output_tokens = state.get("output_tokens", 0)
    model_name = state.get("model_name")
    execution_results = state.get("execution_results") or []

    with Session(engine) as session:
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
            def _safe_json(obj) -> str:
                return json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o))

            for r in execution_results:
                payload = _safe_json(r.get("args", {}))
                response = _safe_json(r["result"]) if r.get("result") is not None else (r.get("error") or "")
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

        if total > _KEEP_LAST and total % _SUMMARY_EVERY == 0:
            messages_to_compress = all_messages[:-_KEEP_LAST]
            chat_session = get_chat_session_by_id(session, chat_session_id)
            existing_summary = chat_session.summary if chat_session else None
            logger.info(f"Regenerating summary ({len(messages_to_compress)} messages to compress)")
            new_summary = _generate_summary(existing_summary, messages_to_compress)
            update_chat_session_summary(session, chat_session_id, new_summary)

        session.commit()

    logger.info(f"Commitment: saved turn for session {chat_session_id} ({total} total messages)")
    return {}
