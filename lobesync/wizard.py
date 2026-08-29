import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from lobesync.agent.models import PROVIDERS, Provider

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


def _pick_provider() -> Provider:
    available = [p for p in PROVIDERS.values() if p.installed]
    missing = [p for p in PROVIDERS.values() if not p.installed]

    if not available:
        console.print("[red]No supported LLM provider packages are installed.[/red]")
        raise SystemExit(1)

    table = Table(title="LLM Providers", header_style="bold cyan")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Provider")
    table.add_column("Suggested model", style="dim")
    for i, provider in enumerate(available, 1):
        table.add_row(str(i), provider.label, provider.default_model)
    console.print(table)

    for provider in missing:
        console.print(
            f"[dim]• {provider.label}: install with 'pip install {provider.package}'[/dim]"
        )

    while True:
        choice = Prompt.ask("[bold yellow]Select a provider[/bold yellow]", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            return available[int(choice) - 1]
        console.print("[red]Invalid selection. Choose a number from the list.[/red]")


def _pick_api_key(provider: Provider) -> str | None:
    if provider.key_kwarg is None:
        return None
    while True:
        api_key = Prompt.ask(
            f"[bold yellow]Enter your {provider.label} API key[/bold yellow]", password=True
        )
        if api_key.strip():
            return api_key.strip()
        console.print("[red]API key cannot be empty.[/red]")


def _pick_database() -> str:
    use_local = Confirm.ask(
        "[bold yellow]Use a local SQLite database?[/bold yellow] (recommended)", default=True
    )
    if use_local:
        db_path = CONFIG_DIR / "lobesync.db"
        console.print(f"[dim]Database will be stored at: {db_path}[/dim]")
        return f"sqlite:///{db_path}"

    return Prompt.ask(
        "[bold yellow]Enter your database URL[/bold yellow] (e.g. sqlite:///path/to/db.sqlite3)"
    )


def _save(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _validate(provider: Provider, model: str) -> None:
    try:
        from lobesync.agent.models import get_chat_model

        get_chat_model()
    except ImportError as e:
        raise SystemExit(f"[red]{e}[/red]") from e
    except TypeError as e:
        raise SystemExit(f"[red]Failed to initialize {provider.label}: {e}[/red]") from e


def run_wizard() -> dict:
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    console.print(
        Panel(
            "[bold]Welcome to Lobesync Setup[/bold]\nYour personal AI assistant for tasks, notes, memories, and checklists.",
            border_style="cyan",
        )
    )
    console.print()

    provider = _pick_provider()

    console.print()
    model = Prompt.ask(
        "[bold yellow]Enter the model name[/bold yellow]",
        default=provider.default_model,
    ).strip()

    console.print()
    api_key = _pick_api_key(provider)

    console.print()
    db_url = _pick_database()

    new_config = {
        "LLM_PROVIDER": provider.id,
        "LLM_MODEL": model,
        "DATABASE_URL": db_url,
    }
    if api_key:
        new_config["LLM_API_KEY"] = api_key

    _save(new_config)
    _validate(provider, model)

    console.print()
    console.print(
        Panel(
            f"[bold green]Setup complete![/bold green]\n"
            f"Provider: [cyan]{provider.label}[/cyan]\n"
            f"Model: [cyan]{model}[/cyan]\n"
            f"Config saved to [cyan]{CONFIG_FILE}[/cyan]",
            border_style="green",
        )
    )
    console.print()

    return new_config


def load_config() -> dict | None:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return None
