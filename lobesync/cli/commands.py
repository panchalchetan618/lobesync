from sqlmodel import Session, select
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from lobesync.db.database import engine
from lobesync.db.models import ChatSession, Message
from lobesync.db.repos.chat_repo import create_chat_session, get_all_chat_sessions, get_chat_session_by_id

console = Console()

HELP_TEXT = """
[bold cyan]Available commands:[/bold cyan]

  [bold]/sessions[/bold]          List all chat sessions
  [bold]/session new[/bold]       Start a new session
  [bold]/session new <name>[/bold] Start a new named session
  [bold]/session <id>[/bold]      Switch to a session by ID
  [bold]/help[/bold]              Show this help

[dim]Everything else is sent to the AI assistant.[/dim]
"""


def _message_count(session: Session, chat_session_id: int) -> int:
    return len(session.exec(
        select(Message).where(Message.chat_session_id == chat_session_id)
    ).all())


def cmd_list_sessions(app_state: dict):
    with Session(engine) as session:
        sessions = get_all_chat_sessions(session) or []

        table = Table(title="Chat Sessions", border_style="cyan", show_lines=True)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Name", style="bold")
        table.add_column("Messages", justify="right")
        table.add_column("Created", style="dim")
        table.add_column("", width=8)

        for s in sessions:
            count = _message_count(session, s.id)
            active = "[bold green]active[/bold green]" if s.id == app_state["chat_session_id"] else ""
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


def _load_memories_context(session: Session) -> str:
    from lobesync.db.repos.memory_repo import get_all_memories
    memories = get_all_memories(session) or []
    return "\n".join([f"- {m.key}: {m.content}" for m in memories])


def cmd_new_session(app_state: dict, name: str | None = None):
    with Session(engine) as session:
        chat_session = create_chat_session(session, name=name)
        session.commit()
        session.refresh(chat_session)
        session_id = chat_session.id
        session_name = chat_session.name or f"Session {session_id}"
        memories_context = _load_memories_context(session)

    app_state["chat_session_id"] = session_id
    app_state["memories_context"] = memories_context
    console.print(f"\n[bold green]Switched to new session:[/bold green] [cyan]{session_name}[/cyan] (ID: {session_id})\n")


def cmd_switch_session(app_state: dict, session_id: int):
    with Session(engine) as session:
        chat_session = get_chat_session_by_id(session, session_id)
        if not chat_session:
            console.print(f"\n[red]Session {session_id} not found.[/red]\n")
            return
        session_name = chat_session.name or f"Session {session_id}"
        memories_context = _load_memories_context(session)

    app_state["chat_session_id"] = session_id
    app_state["memories_context"] = memories_context
    console.print(f"\n[bold green]Switched to:[/bold green] [cyan]{session_name}[/cyan] (ID: {session_id})\n")


def handle_command(raw: str, app_state: dict) -> bool:
    """
    Handle /commands. Returns True if the input was a command, False otherwise.
    """
    parts = raw.strip().split()
    cmd = parts[0].lower()

    if cmd == "/help":
        console.print(Panel(HELP_TEXT, border_style="cyan", padding=(0, 2)))
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

    console.print(f"[red]Unknown command: {cmd}[/red]  Type [bold]/help[/bold] for available commands.")
    return True
