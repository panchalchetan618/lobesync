import logging
import os

from rich.console import Console
from rich.panel import Panel
from sqlmodel import Session

from lobesync.wizard import BANNER, load_config, run_wizard

logging.basicConfig(level=logging.WARNING)
console = Console()


def _ensure_configured():
    config = load_config()
    if config:
        return
    if os.getenv("DATABASE_URL") and (os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        return
    run_wizard()
    from lobesync.config import config

    config.reload()


def main():
    _ensure_configured()

    from lobesync.agent.graph import build_graph
    from lobesync.cli.commands import handle_command
    from lobesync.db.database import get_engine, init_db
    from lobesync.db.repos.chat_repo import create_chat_session
    from lobesync.db.repos.memory_repo import get_all_memories

    init_db()

    with Session(get_engine()) as session:
        chat_session = create_chat_session(session, name="Lobesync")
        session.commit()
        session.refresh(chat_session)
        chat_session_id = chat_session.id

        memories = get_all_memories(session) or []
        memories_context = "\n".join([f"- {m.key}: {m.content}" for m in memories])

    graph = build_graph()
    app_state = {"chat_session_id": chat_session_id, "memories_context": memories_context}

    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    console.print(
        Panel(
            "[bold]Personal AI Assistant[/bold]  ·  Tasks · Notes · Memories · Checklists\n"
            "[dim]Type [bold white]/help[/bold white] for commands  ·  [bold white]exit[/bold white] to quit[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()

    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if user_input.startswith("/"):
            handle_command(user_input, app_state)
            continue

        graph.invoke(
            {
                "user_query": user_input,
                "chat_session_id": app_state["chat_session_id"],
                "memories_context": app_state.get("memories_context", ""),
                "plan": None,
                "execution_results": [],
                "final_response": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "model_name": None,
                "error": None,
            }
        )


if __name__ == "__main__":
    main()
