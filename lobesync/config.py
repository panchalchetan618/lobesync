import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env")

_CONFIG_FILE = Path.home() / ".lobesync" / "config.json"


def _read_file() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}


class Config:
    """Reads config lazily so values written after import (e.g. by the setup
    wizard) are picked up."""

    _cache: dict | None = None

    def _load(self) -> dict:
        if self._cache is None:
            self._cache = _read_file()
        return self._cache

    def reload(self) -> None:
        self._cache = _read_file()

    @property
    def DATABASE_URL(self) -> str | None:
        return self._load().get("DATABASE_URL") or os.getenv("DATABASE_URL")

    @property
    def LLM_PROVIDER(self) -> str:
        return self._load().get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "anthropic"

    @property
    def LLM_MODEL(self) -> str:
        return (
            self._load().get("LLM_MODEL") or os.getenv("LLM_MODEL") or "claude-haiku-4-5-20251001"
        )

    @property
    def LLM_API_KEY(self) -> str | None:
        file_cfg = self._load()
        return (
            file_cfg.get("LLM_API_KEY")
            or os.getenv("LLM_API_KEY")
            or file_cfg.get("ANTHROPIC_API_KEY")  # legacy
            or os.getenv("ANTHROPIC_API_KEY")
        )


config = Config()
