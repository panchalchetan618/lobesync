import sys
from collections.abc import Sequence

import questionary
from rich.console import Console
from rich.prompt import Confirm, Prompt

from lobesync.agent.models import PROVIDERS, Provider
from lobesync.config import validate_openai_base_url

console = Console()


def select_option(message: str, options: Sequence[tuple[str, str]]) -> str | None:
    """Select an option with arrow keys, with a simple fallback for basic terminals."""
    if sys.stdin.isatty() and sys.stdout.isatty():
        return questionary.select(
            message,
            choices=[questionary.Choice(label, value=value) for label, value in options],
        ).ask()

    console.print(message)
    for index, (label, _) in enumerate(options, 1):
        console.print(f"  {index}. {label}")
    while True:
        choice = Prompt.ask("Select an option", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][1]
        console.print("[red]Enter one of the listed numbers.[/red]")


def select_provider() -> Provider | None:
    """Select one of Lobesync's supported providers."""
    provider_id = select_option(
        "Select a provider",
        [
            (f"{provider.label} — suggested: {provider.default_model}", provider.id)
            for provider in PROVIDERS.values()
        ],
    )
    return PROVIDERS.get(provider_id) if provider_id else None


def prompt_openai_base_url(default: str) -> str:
    """Prompt for and validate an OpenAI-compatible base URL."""
    console.print(
        "[yellow]This endpoint receives the prompt context required for each request.[/yellow]"
    )
    while True:
        value = Prompt.ask("OpenAI-compatible base URL", default=default)
        try:
            return validate_openai_base_url(value)
        except ValueError as error:
            console.print(f"[red]{error}[/red]")


def confirm_action(message: str, *, default: bool = False) -> bool:
    """Ask for an explicit yes/no decision, defaulting to the safe answer."""
    if sys.stdin.isatty() and sys.stdout.isatty():
        answer = questionary.confirm(message, default=default).ask()
        return bool(answer)
    return Confirm.ask(message, default=default)
