import logging
from collections.abc import Sequence
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from sqlmodel import Session

from lobesync.agent.models import get_chat_model, get_model_name, use_prompt_caching
from lobesync.agent.state import AgentState
from lobesync.agent.tools import MAKE_PLAN_TOOL, PLANNER_SYSTEM_PROMPT
from lobesync.db.database import get_engine
from lobesync.db.models import Message, MessageRole
from lobesync.db.repos.chat_repo import (
    get_chat_session_by_id,
    get_messages_by_session,
    get_tool_calls_by_message,
)

console = Console()

logger = logging.getLogger(__name__)

_LAST_N = 5


def _build_system(memories_context: str) -> str:
    blocks = [PLANNER_SYSTEM_PROMPT]
    if memories_context:
        blocks.append(f"## What I know about you:\n{memories_context}")
    return "\n\n".join(blocks)


def _build_history(
    session: Session, messages: Sequence[Message], summary: str | None
) -> list[BaseMessage]:
    history = []

    if summary:
        history += [
            HumanMessage(content="Let's continue our conversation."),
            AIMessage(content=f"Here's what we discussed so far:\n{summary}"),
        ]

    for msg in messages[-_LAST_N:]:
        role = "user" if msg.role == MessageRole.USER else "assistant"
        content = msg.content

        if msg.role == MessageRole.AGENT:
            tool_calls = get_tool_calls_by_message(session, msg.id) if msg.id else []
            if tool_calls:
                tool_lines = "\n".join(
                    [f"[Tool: {tc.tool_name} | Result: {tc.response[:300]}]" for tc in tool_calls]
                )
                content = f"{tool_lines}\n\n{content}"

        if role == "user":
            history.append(HumanMessage(content=content))
        else:
            history.append(AIMessage(content=content))

    return history


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""


def planner_node(state: AgentState) -> dict:
    """
    Single LLM call with tool_choice=auto.
    System prompt = static instructions + memories (cached, loaded once per session).
    Messages = summary + last 5 messages + current query.
    """
    user_query = state["user_query"]
    chat_session_id = state["chat_session_id"]
    memories_context = state.get("memories_context", "")

    with Session(get_engine()) as session:
        prior_messages = get_messages_by_session(session, chat_session_id) or []
        chat_session = get_chat_session_by_id(session, chat_session_id)
        summary = chat_session.summary if chat_session else None
        history = _build_history(session, prior_messages, summary)
    history.append(HumanMessage(content=user_query))

    model = get_chat_model(max_tokens=4096).bind_tools([MAKE_PLAN_TOOL], tool_choice="auto")

    direct_response = None
    plan_input = None
    input_tokens = 0
    output_tokens = 0
    accumulated = ""

    live = None
    console.print("\n[bold blue]Lobesync:[/bold blue]")
    full_message: AIMessage | None = None
    call_kwargs = {"cache_control": {"type": "ephemeral"}} if use_prompt_caching() else {}
    for chunk in model.stream(
        [SystemMessage(content=_build_system(memories_context)), *history],
        **call_kwargs,  # type: ignore[arg-type]
    ):
        full_message = cast(
            AIMessage,
            chunk if full_message is None else full_message + chunk,
        )
        text = _extract_text(chunk.content)
        if text:
            accumulated += text
            if live is None:
                live = Live(Markdown(""), console=console, refresh_per_second=15)
                live.start()
            live.update(Markdown(accumulated))

    if live:
        live.stop()
        console.print()

    if full_message is None:
        logger.error("Planner returned no response — defaulting to empty plan")
        return {"plan": {"atomic_groups": [], "non_atomic": []}}

    usage: dict[str, Any] = dict(full_message.usage_metadata or {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    for tc in full_message.tool_calls or []:
        if tc.get("name") == "make_plan":
            plan_input = tc.get("args")

    if _extract_text(full_message.content).strip():
        direct_response = _extract_text(full_message.content).strip()

    if direct_response:
        logger.info("Planner responded directly")
        return {
            "plan": {"atomic_groups": [], "non_atomic": []},
            "final_response": direct_response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_name": get_model_name(),
        }

    if plan_input is None:
        logger.error("Planner returned neither text nor make_plan — defaulting to empty plan")
        plan_input = {"atomic_groups": [], "non_atomic": []}

    logger.info(
        f"Plan: atomic_groups={len(plan_input.get('atomic_groups', []))}, non_atomic={len(plan_input.get('non_atomic', []))}"
    )
    return {
        "plan": plan_input,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_name": get_model_name(),
    }
