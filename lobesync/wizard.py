import json
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

CONFIG_DIR = Path.home() / ".lobesync"
CONFIG_FILE = CONFIG_DIR / "config.json"

console = Console()

BANNER = """
██╗      ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███╗   ██╗ ██████╗
██║     ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝████╗  ██║██╔════╝
██║     ██║   ██║██████╔╝█████╗  ███████╗ ╚████╔╝ ██╔██╗ ██║██║
██║     ██║   ██║██╔══██╗██╔══╝  ╚════██║  ╚██╔╝  ██║╚██╗██║██║
███████╗╚██████╔╝██████╔╝███████╗███████║   ██║   ██║ ╚████║╚██████╗
╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝
"""


def run_wizard() -> dict:
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    console.print(Panel(
        "[bold]Welcome to Lobesync Setup[/bold]\nYour personal AI assistant for tasks, notes, memories, and checklists.",
        border_style="cyan"
    ))
    console.print()

    # API Key
    while True:
        api_key = Prompt.ask("[bold yellow]Enter your Anthropic API key[/bold yellow]", password=True)
        if api_key.startswith("sk-ant-"):
            break
        console.print("[red]Invalid key format. Anthropic API keys start with 'sk-ant-'[/red]")

    # Database
    console.print()
    use_local = Confirm.ask("[bold yellow]Use a local SQLite database?[/bold yellow] (recommended)", default=True)

    if use_local:
        db_path = CONFIG_DIR / "lobesync.db"
        db_url = f"sqlite:///{db_path}"
        console.print(f"[dim]Database will be stored at: {db_path}[/dim]")
    else:
        db_url = Prompt.ask("[bold yellow]Enter your database URL[/bold yellow] (e.g. sqlite:///path/to/db.sqlite3)")

    config = {
        "ANTHROPIC_API_KEY": api_key,
        "DATABASE_URL": db_url,
    }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

    console.print()
    console.print(Panel(
        f"[bold green]Setup complete![/bold green]\nConfig saved to [cyan]{CONFIG_FILE}[/cyan]",
        border_style="green"
    ))
    console.print()

    return config


def load_config() -> dict | None:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return None
