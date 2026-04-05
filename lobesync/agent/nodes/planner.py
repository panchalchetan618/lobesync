import anthropic
import logging
from sqlmodel import Session
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

from lobesync.config import config
from lobesync.db.database import engine
from lobesync.db.models import MessageRole
from lobesync.db.repos.chat_repo import get_messages_by_session, get_chat_session_by_id, get_tool_calls_by_message
from lobesync.agent.state import AgentState
from lobesync.agent.tools import MAKE_PLAN_TOOL, PLANNER_SYSTEM_PROMPT

console = Console()

logger = logging.getLogger(__name__)

_LAST_N = 5


def _build_system(memories_context: str) -> list[dict]:
    blocks = [
        {
            "type": "text",
            "text": PLANNER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if memories_context:
        blocks.append({
            "type": "text",
            "text": f"## What I know about you:\n{memories_context}",
            "cache_control": {"type": "ephemeral"},
        })
    return blocks


def _build_history(session, messages: list, summary: str | None) -> list[dict]:
    history = []

    if summary:
        history += [
            {"role": "user", "content": "Let's continue our conversation."},
            {"role": "assistant", "content": f"Here's what we discussed so far:\n{summary}"},
        ]

    for msg in messages[-_LAST_N:]:
        role = "user" if msg.role == MessageRole.USER else "assistant"
        content = msg.content

        if msg.role == MessageRole.AGENT:
            tool_calls = get_tool_calls_by_message(session, msg.id) or []
            if tool_calls:
                tool_lines = "\n".join([
                    f"[Tool: {tc.tool_name} | Result: {tc.response[:300]}]"
                    for tc in tool_calls
                ])
                content = f"{tool_lines}\n\n{content}"

        history.append({"role": role, "content": content})

    return history


def planner_node(state: AgentState) -> dict:
    """
    Single LLM call with tool_choice=auto.
    System prompt = static instructions + memories (cached, loaded once per session).
    Messages = summary + last 5 messages + current query.
    """
    user_query = state["user_query"]
    chat_session_id = state["chat_session_id"]
    memories_context = state.get("memories_context", "")

    with Session(engine) as session:
        prior_messages = get_messages_by_session(session, chat_session_id) or []
        chat_session = get_chat_session_by_id(session, chat_session_id)
        summary = chat_session.summary if chat_session else None
        history = _build_history(session, prior_messages, summary)
    history.append({"role": "user", "content": user_query})

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    direct_response = None
    plan_input = None
    input_tokens = 0
    output_tokens = 0
    accumulated = ""

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=_build_system(memories_context),
        messages=history,
        tools=[MAKE_PLAN_TOOL],
        tool_choice={"type": "auto"},
    ) as stream:
        live = None
        for event in stream:
            if event.type == "content_block_start" and hasattr(event.content_block, "type"):
                if event.content_block.type == "text" and live is None:
                    console.print("\n[bold blue]Lobesync:[/bold blue]")
                    live = Live(Markdown(""), console=console, refresh_per_second=15)
                    live.start()
            if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                accumulated += event.delta.text
                if live:
                    live.update(Markdown(accumulated))

        if live:
            live.stop()
            console.print()

        final_message = stream.get_final_message()
        input_tokens = final_message.usage.input_tokens
        output_tokens = final_message.usage.output_tokens

        for block in final_message.content:
            if block.type == "text" and block.text.strip():
                direct_response = block.text
            elif block.type == "tool_use" and block.name == "make_plan":
                plan_input = block.input

    if direct_response:
        logger.info("Planner responded directly")
        return {
            "plan": {"atomic_groups": [], "non_atomic": []},
            "final_response": direct_response,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_name": "claude-haiku-4-5-20251001",
        }

    if plan_input is None:
        logger.error("Planner returned neither text nor make_plan — defaulting to empty plan")
        plan_input = {"atomic_groups": [], "non_atomic": []}

    logger.info(f"Plan: atomic_groups={len(plan_input.get('atomic_groups', []))}, non_atomic={len(plan_input.get('non_atomic', []))}")
    return {"plan": plan_input}
