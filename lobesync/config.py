from dotenv import load_dotenv
import os
import json
from pathlib import Path

load_dotenv('.env')

_CONFIG_FILE = Path.home() / ".lobesync" / "config.json"


def _load() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}


_file_config = _load()


class Config:
    DATABASE_URL: str = _file_config.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    ANTHROPIC_API_KEY: str = _file_config.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")


config = Config()
