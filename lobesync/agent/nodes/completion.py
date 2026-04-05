import anthropic
import logging
from sqlmodel import Session
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

from lobesync.config import config
from lobesync.db.database import engine
from lobesync.db.models import MessageRole
from lobesync.db.repos.chat_repo import get_messages_by_session
from lobesync.agent.state import AgentState

console = Console()


logger = logging.getLogger(__name__)

COMPLETION_SYSTEM_PROMPT = """You are Lobesync, a personal AI assistant. You help the user manage tasks, notes, memories, and checklists.

When tool results are provided in the user message, summarize what was done naturally and concisely.
Always mention the ID of any created or retrieved item (e.g. "Task created with ID 3") so the user can reference it later.
If an operation failed, acknowledge it clearly and suggest what the user can do.
If no tools were called, just respond naturally as a helpful assistant."""

_COMPLETION_SYSTEM = [
    {
        "type": "text",
        "text": COMPLETION_SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]

_COMPLETION_MODEL = "claude-haiku-4-5-20251001"


def _build_history(messages) -> list[dict]:
    history = []
    for msg in messages:
        role = "user" if msg.role == MessageRole.USER else "assistant"
        history.append({"role": role, "content": msg.content})
    return history


def _format_results(execution_results: list[dict]) -> str:
    if not execution_results:
        return ""
    lines = []
    for r in execution_results:
        if r["error"]:
            lines.append(f"- {r['tool']}: FAILED — {r['error']}")
        else:
            lines.append(f"- {r['tool']}: SUCCESS — {r['result']}")
    return "\n".join(lines)


def completion_node(state: AgentState) -> dict:
    """
    Generates the final natural language response.
    Loads conversation history, injects tool results, calls Claude, saves messages to DB.
    """
    chat_session_id = state["chat_session_id"]
    user_query = state["user_query"]
    execution_results = state.get("execution_results") or []

    with Session(engine) as session:
        prior_messages = get_messages_by_session(session, chat_session_id) or []
        history = _build_history(prior_messages)

        user_content = user_query
        results_text = _format_results(execution_results)
        if results_text:
            user_content = f"{user_query}\n\n[Tool results:\n{results_text}]"

        history.append({"role": "user", "content": user_content})

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        accumulated = ""
        console.print("\n[bold blue]Lobesync:[/bold blue]")
        with client.messages.stream(
            model=_COMPLETION_MODEL,
            max_tokens=1024,
            system=_COMPLETION_SYSTEM,
            messages=history,
        ) as stream:
            with Live(Markdown(accumulated), console=console, refresh_per_second=15) as live:
                for text in stream.text_stream:
                    accumulated += text
                    live.update(Markdown(accumulated))
            final_message = stream.get_final_message()
        console.print()

        final_response = final_message.content[0].text
        input_tokens = final_message.usage.input_tokens
        output_tokens = final_message.usage.output_tokens

    logger.info(f"Completion: {input_tokens} in / {output_tokens} out tokens")
    return {
        "final_response": final_response,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_name": _COMPLETION_MODEL,
    }
