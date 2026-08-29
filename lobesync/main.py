import logging
import os

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from sqlmodel import Session

from lobesync.cli.prompts import confirm_action
from lobesync.services.memory_context import load_memories_context
from lobesync.wizard import BANNER, load_config, run_wizard

logging.basicConfig(level=logging.WARNING)
console = Console()


def _ensure_configured():
    configured_values = load_config()
    supported_providers = {"anthropic", "openai", "google", "custom"}
    if (
        configured_values
        and str(configured_values.get("DATABASE_URL", "")).startswith("sqlite")
        and configured_values.get("LLM_PROVIDER", "anthropic") in supported_providers
    ):
        return
    environment_database = os.getenv("DATABASE_URL")
    if environment_database and environment_database.startswith("sqlite") and (
        os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    ):
        return

    if configured_values or environment_database:
        console.print(
            "[yellow]Remote databases are not supported by the open-source edition. "
            "Set up local storage to continue.[/yellow]"
        )
    run_wizard()
    from lobesync.config import config

    config.reload()


def _memory_changed(execution_results: list[dict]) -> bool:
    return any(
        result.get("error") is None and "memory" in result.get("tool", "")
        for result in execution_results
    )


def _bulk_delete_targets(plan: dict) -> list[str]:
    steps = list(plan.get("non_atomic", []))
    for group in plan.get("atomic_groups", []):
        if isinstance(group, list):
            steps.extend(group)

    targets = []
    for step in steps:
        if not isinstance(step, dict) or not str(step.get("tool", "")).startswith("delete_"):
            continue
        args = step.get("args", {})
        if not isinstance(args, dict):
            args = {}
        identifier = next((value for key, value in args.items() if key.endswith("_id")), None)
        label = step["tool"].removeprefix("delete_").replace("_", " ")
        targets.append(f"{label} (ID: {identifier})" if identifier is not None else label)
    return targets


def _invoke_graph(graph, app_state: dict, user_query: str, approved_bulk_plan: dict | None = None) -> dict:
    return graph.invoke(
        {
            "user_query": user_query,
            "chat_session_id": app_state["chat_session_id"],
            "memories_context": app_state.get("memories_context", ""),
            "plan": None,
            "execution_results": [],
            "final_response": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "model_name": None,
            "error": None,
            "approved_bulk_plan": approved_bulk_plan,
        }
    )


def _render_execution_result(result: dict) -> None:
    if result.get("execution_results") and result.get("final_response"):
        console.print("\n[bold blue]Lobesync:[/bold blue]")
        console.print(Markdown(result["final_response"]))
        console.print()


def main():
    _ensure_configured()

    from lobesync.agent.graph import build_graph
    from lobesync.cli.commands import handle_command
    from lobesync.config import config
    from lobesync.db.database import get_engine, init_db
    from lobesync.db.repos.chat_repo import create_chat_session

    init_db()

    with Session(get_engine()) as session:
        chat_session = create_chat_session(session, name="Lobesync")
        if chat_session is None or chat_session.id is None:
            raise RuntimeError("Could not create a chat session")
        session.commit()
        session.refresh(chat_session)
        chat_session_id = chat_session.id
        memories_context = load_memories_context(session)

    graph = build_graph()
    app_state = {
        "chat_session_id": chat_session_id,
        "memories_context": memories_context,
    }

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

        try:
            result = _invoke_graph(graph, app_state, user_input)
        except Exception:
            logging.info("Conversation turn failed")
            console.print("[red]That request could not be completed. Your data was not changed.[/red]")
            continue

        if result.get("bulk_delete_confirmation_required"):
            targets = _bulk_delete_targets(result["plan"])
            console.print("\n[yellow]You are about to delete:[/yellow]")
            for target in targets:
                console.print(f"  • {target}")
            if confirm_action("Are you sure?", default=False):
                try:
                    result = _invoke_graph(
                        graph,
                        app_state,
                        "Confirmed bulk deletion.",
                        result["plan"],
                    )
                except Exception:
                    logging.info("Confirmed bulk deletion failed")
                    console.print("[red]The bulk deletion could not be completed.[/red]")
                    continue
                _render_execution_result(result)
            else:
                console.print("[dim]Bulk deletion cancelled.[/dim]")
        else:
            _render_execution_result(result)

        execution_results = result.get("execution_results") or []
        if config.MEMORY_ENABLED and _memory_changed(execution_results):
            with Session(get_engine()) as session:
                app_state["memories_context"] = load_memories_context(session)


if __name__ == "__main__":
    main()
