import json

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from lobesync.agent.models import Provider
from lobesync.cli.prompts import prompt_openai_base_url, select_option, select_provider
from lobesync.config import config_file_path, store_api_key, write_file_config

console = Console()

BANNER = """
██╗      ██████╗ ██████╗ ███████╗███████╗██╗   ██╗███╗   ██╗ ██████╗
██║     ██╔═══██╗██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝████╗  ██║██╔════╝
██║     ██║   ██║██████╔╝█████╗  ███████╗ ╚████╔╝ ██╔██╗ ██║██║
██║     ██║   ██║██╔══██╗██╔══╝  ╚════██║  ╚██╔╝  ██║╚██╗██║██║
███████╗╚██████╔╝██████╔╝███████╗███████║   ██║   ██║ ╚████║╚██████╗
╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝
"""


def _pick_api_key(provider: Provider) -> str | None:
    if provider.key_kwarg is None:
        return None
    if provider.api_key_optional:
        choice = select_option(
            "Authentication",
            [("No API key", "none"), ("Enter an API key", "set")],
        )
        if choice != "set":
            return None
    while True:
        api_key = Prompt.ask(
            f"[bold yellow]Enter your {provider.label} API key[/bold yellow]", password=True
        )
        if api_key.strip():
            return api_key.strip()
        console.print("[red]API key cannot be empty.[/red]")


def _pick_database() -> str:
    db_path = config_file_path().with_name("lobesync.db")
    console.print(f"[dim]Your data will be stored locally at: {db_path}[/dim]")
    return f"sqlite:///{db_path}"


def _validate(provider: Provider) -> None:
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

    provider = select_provider()
    if provider is None:
        raise SystemExit(1)

    console.print()
    model = Prompt.ask(
        "[bold yellow]Enter the model name[/bold yellow]",
        default=provider.default_model,
    ).strip()

    console.print()
    api_key = _pick_api_key(provider)

    console.print()
    base_url = (
        prompt_openai_base_url("http://localhost:11434/v1")
        if provider.supports_custom_base_url
        else None
    )

    console.print()
    db_url = _pick_database()

    console.print()
    memory_enabled = Confirm.ask(
        "[bold yellow]Enable cross-session memory?[/bold yellow]", default=False
    )

    new_config = {
        "LLM_PROVIDER": provider.id,
        "LLM_MODEL": model,
        "DATABASE_URL": db_url,
        "MEMORY_ENABLED": memory_enabled,
    }
    if base_url:
        new_config["LLM_BASE_URL"] = base_url
    write_file_config(new_config)
    if api_key:
        store_api_key(provider.id, api_key)

    from lobesync.config import config

    config.reload()
    _validate(provider)

    console.print()
    console.print(
        Panel(
            f"[bold green]Setup complete![/bold green]\n"
            f"Provider: [cyan]{provider.label}[/cyan]\n"
            f"Model: [cyan]{model}[/cyan]\n"
            f"Config saved to [cyan]{config_file_path()}[/cyan]",
            border_style="green",
        )
    )
    console.print()

    return new_config


def load_config() -> dict | None:
    config_file = config_file_path()
    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))
    return None
