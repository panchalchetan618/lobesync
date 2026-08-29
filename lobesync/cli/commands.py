from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from sqlmodel import Session, select

from lobesync.agent.models import get_chat_model
from lobesync.cli.prompts import prompt_openai_base_url, select_option, select_provider
from lobesync.config import config, delete_api_key, store_api_key
from lobesync.db.database import get_engine
from lobesync.db.models import Message
from lobesync.db.repos.chat_repo import (
    create_chat_session,
    get_all_chat_sessions,
    get_chat_session_by_id,
)
from lobesync.services.memory_context import load_memories_context

console = Console()

HELP_TEXT = """
[bold cyan]Available commands:[/bold cyan]

  [bold]/sessions[/bold]          List all chat sessions
  [bold]/session new[/bold]       Start a new session
  [bold]/session new <name>[/bold] Start a new named session
  [bold]/session <id>[/bold]      Switch to a session by ID
  [bold]/memory[/bold]            Show memory status
  [bold]/memory on|off[/bold]     Enable or disable cross-session memory
  [bold]/configure[/bold]         Change provider, model, API key, or custom endpoint
  [bold]/help[/bold]              Show this help

[dim]Everything else is sent to the AI assistant.[/dim]
"""


def _message_count(session: Session, chat_session_id: int) -> int:
    return len(
        session.exec(select(Message).where(Message.chat_session_id == chat_session_id)).all()
    )


def cmd_list_sessions(app_state: dict):
    with Session(get_engine()) as session:
        sessions = get_all_chat_sessions(session) or []

        table = Table(title="Chat Sessions", border_style="cyan", show_lines=True)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Name", style="bold")
        table.add_column("Messages", justify="right")
        table.add_column("Created", style="dim")
        table.add_column("", width=8)

        for s in sessions:
            if s.id is None:
                continue
            count = _message_count(session, s.id)
            active = (
                "[bold green]active[/bold green]" if s.id == app_state["chat_session_id"] else ""
            )
            table.add_row(
                str(s.id),
                s.name or f"Session {s.id}",
                str(count),
                s.created_at.strftime("%b %d %H:%M"),
                active,
            )

    console.print()
    console.print(table)
    console.print()


def cmd_new_session(app_state: dict, name: str | None = None):
    with Session(get_engine()) as session:
        chat_session = create_chat_session(session, name=name)
        if chat_session is None or chat_session.id is None:
            raise RuntimeError("Failed to create chat session")
        session.commit()
        session.refresh(chat_session)
        session_id = chat_session.id
        session_name = chat_session.name or f"Session {session_id}"
        memories_context = load_memories_context(session)

    app_state["chat_session_id"] = session_id
    app_state["memories_context"] = memories_context
    console.print(
        f"\n[bold green]Switched to new session:[/bold green] [cyan]{session_name}[/cyan] (ID: {session_id})\n"
    )


def cmd_switch_session(app_state: dict, session_id: int):
    with Session(get_engine()) as session:
        chat_session = get_chat_session_by_id(session, session_id)
        if not chat_session:
            console.print(f"\n[red]Session {session_id} not found.[/red]\n")
            return
        session_name = chat_session.name or f"Session {session_id}"
        memories_context = load_memories_context(session)

    app_state["chat_session_id"] = session_id
    app_state["memories_context"] = memories_context
    console.print(
        f"\n[bold green]Switched to:[/bold green] [cyan]{session_name}[/cyan] (ID: {session_id})\n"
    )


def _configure_api_key(provider_id: str, *, optional: bool) -> bool:
    has_key = bool(config.LLM_API_KEY) if config.LLM_PROVIDER == provider_id else False
    options = [("Enter a new API key", "set")]
    if has_key:
        options.insert(0, ("Keep the existing API key", "keep"))
    if optional:
        options.insert(0, ("Use no API key", "clear"))

    choice = select_option("API key", options)
    if choice is None:
        return False
    if choice == "set":
        api_key = Prompt.ask("API key", password=True).strip()
        if not api_key:
            console.print("[yellow]Configuration cancelled because the API key was empty.[/yellow]")
            return False
        store_api_key(provider_id, api_key)
    elif choice == "clear":
        delete_api_key(provider_id)
    return True


def cmd_configure() -> None:
    choice = select_option(
        "What would you like to configure?",
        [
            ("Provider and model", "provider"),
            ("Test current connection", "test"),
            ("Show active configuration", "show"),
        ],
    )
    if choice == "show":
        display_base_url = config.LLM_BASE_URL or "Not set"
        console.print(
            Panel(
                f"Provider: [cyan]{config.LLM_PROVIDER}[/cyan]\n"
                f"Model: [cyan]{config.LLM_MODEL}[/cyan]\n"
                f"Base URL: [cyan]{display_base_url}[/cyan]\n"
                f"API key: [cyan]{'configured' if config.LLM_API_KEY else 'not configured'}[/cyan]",
                title="Active configuration",
                border_style="cyan",
            )
        )
        return
    if choice == "test":
        try:
            get_chat_model(max_tokens=8).invoke("Reply with OK.")
        except Exception as error:
            console.print(f"[red]Connection test failed: {error}[/red]")
        else:
            console.print("[green]Connection succeeded.[/green]")
        return
    if choice != "provider":
        return

    provider = select_provider()
    if provider is None:
        return
    model = Prompt.ask("Model", default=provider.default_model).strip()
    if not model:
        console.print("[red]Model cannot be empty.[/red]")
        return
    base_url = (
        prompt_openai_base_url(config.LLM_BASE_URL or "http://localhost:11434/v1")
        if provider.supports_custom_base_url
        else None
    )
    if not _configure_api_key(provider.id, optional=provider.api_key_optional):
        return
    config.update_llm_settings(provider.id, model, base_url)
    console.print("[green]Configuration saved. It will be used for your next request.[/green]")


def handle_command(raw: str, app_state: dict) -> bool:
    """
    Handle /commands. Returns True if the input was a command, False otherwise.
    """
    parts = raw.strip().split()
    cmd = parts[0].lower()

    if cmd == "/help":
        console.print(Panel(HELP_TEXT, border_style="cyan", padding=(0, 2)))
        return True

    if cmd == "/memory":
        if len(parts) == 1:
            status = "enabled" if config.MEMORY_ENABLED else "disabled"
            console.print(f"[cyan]Cross-session memory is {status}.[/cyan]")
        elif len(parts) == 2 and parts[1].lower() in {"on", "off"}:
            enabled = parts[1].lower() == "on"
            config.set_memory_enabled(enabled)
            app_state["memories_context"] = ""
            if enabled:
                with Session(get_engine()) as session:
                    app_state["memories_context"] = load_memories_context(session)
            console.print(
                "[green]Cross-session memory enabled.[/green]"
                if enabled
                else "[yellow]Cross-session memory disabled. Existing memories remain local.[/yellow]"
            )
        else:
            console.print("[red]Usage: /memory, /memory on, or /memory off[/red]")
        return True

    if cmd == "/configure":
        cmd_configure()
        return True

    if cmd in ("/session", "/sessions"):
        if len(parts) == 1 or (len(parts) == 2 and parts[1] == "list"):
            cmd_list_sessions(app_state)
        elif parts[1] == "new":
            name = " ".join(parts[2:]) if len(parts) > 2 else None
            cmd_new_session(app_state, name)
        else:
            try:
                cmd_switch_session(app_state, int(parts[1]))
            except ValueError:
                console.print("[red]Usage: /session, /session new [name], /session <id>[/red]")
        return True

    console.print(
        f"[red]Unknown command: {cmd}[/red]  Type [bold]/help[/bold] for available commands."
    )
    return True
