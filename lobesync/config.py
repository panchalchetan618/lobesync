import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import keyring
from dotenv import load_dotenv
from keyring.errors import KeyringError

load_dotenv(".env")

_CONFIG_FILE = Path.home() / ".lobesync" / "config.json"
_KEYRING_SERVICE = "lobesync"
_LEGACY_API_KEY_FIELDS = ("LLM_API_KEY", "ANTHROPIC_API_KEY")

logger = logging.getLogger(__name__)


def config_file_path() -> Path:
    """Return the location of Lobesync's non-secret configuration file."""
    return _CONFIG_FILE


def _read_file() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not read configuration from {_CONFIG_FILE}") from error
    return {}


def write_file_config(values: dict) -> None:
    """Persist non-secret preferences with restrictive permissions where supported."""
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        _CONFIG_FILE.chmod(0o600)


def store_api_key(provider_id: str, api_key: str) -> None:
    """Store an API key in the operating system credential store."""
    try:
        keyring.set_password(_KEYRING_SERVICE, provider_id, api_key)
    except KeyringError as error:
        raise RuntimeError(
            "Could not store the API key in the operating system credential store. "
            "Set LLM_API_KEY in your environment instead."
        ) from error


def delete_api_key(provider_id: str) -> None:
    try:
        keyring.delete_password(_KEYRING_SERVICE, provider_id)
    except keyring.errors.PasswordDeleteError:
        return
    except KeyringError as error:
        raise RuntimeError("Could not remove the API key from the credential store.") from error


def get_api_key(provider_id: str, *, allow_environment: bool = True) -> str | None:
    """Read a key from the credential store, falling back to environment variables."""
    try:
        stored_key = keyring.get_password(_KEYRING_SERVICE, provider_id)
    except KeyringError:
        stored_key = None
    if stored_key or not allow_environment:
        return stored_key
    return os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")


def _migrate_legacy_api_key(values: dict) -> dict:
    """Move a legacy plaintext key to keyring without risking data loss."""
    legacy_key = next((values.get(field) for field in _LEGACY_API_KEY_FIELDS if values.get(field)), None)
    if not legacy_key:
        return values

    provider_id = values.get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "anthropic"
    try:
        store_api_key(str(provider_id), str(legacy_key))
    except RuntimeError:
        # Keep the old value so the user does not lose access if keyring is unavailable.
        logger.warning(
            "Could not migrate a legacy API key to the operating system credential store. "
            "The existing local configuration was left unchanged."
        )
        return values

    migrated_values = values.copy()
    for field in _LEGACY_API_KEY_FIELDS:
        migrated_values.pop(field, None)
    write_file_config(migrated_values)
    logger.info("Migrated a legacy API key to the operating system credential store")
    return migrated_values


def validate_openai_base_url(value: str) -> str:
    """Accept HTTPS endpoints and explicitly local HTTP endpoints only."""
    parsed = urlsplit(value.strip())
    hostname = parsed.hostname
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("The base URL cannot contain credentials, query parameters, or fragments")
    if not hostname:
        raise ValueError("Enter a complete OpenAI-compatible server URL")
    if parsed.scheme == "https" or (parsed.scheme == "http" and hostname in local_hosts):
        # OpenAI's client resolves endpoint paths relative to this URL. The trailing
        # slash preserves a configured path such as `/v1` during that resolution.
        path_parts = [part for part in parsed.path.split("/") if part]
        path = f"/{'/'.join(path_parts or ['v1'])}/"
        return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    raise ValueError("Use HTTPS, or HTTP only for localhost, 127.0.0.1, or ::1")


class Config:
    """Reads config lazily so values written after import (e.g. by the setup
    wizard) are picked up."""

    _cache: dict | None = None

    def _load(self) -> dict:
        if self._cache is None:
            self._cache = _migrate_legacy_api_key(_read_file())
        return self._cache

    def reload(self) -> None:
        self._cache = _migrate_legacy_api_key(_read_file())

    def set_memory_enabled(self, enabled: bool) -> None:
        values = self._load().copy()
        values["MEMORY_ENABLED"] = enabled
        write_file_config(values)
        self._cache = values

    def update_llm_settings(self, provider: str, model: str, base_url: str | None = None) -> None:
        values = self._load().copy()
        values["LLM_PROVIDER"] = provider
        values["LLM_MODEL"] = model
        if base_url:
            values["LLM_BASE_URL"] = validate_openai_base_url(base_url)
        else:
            values.pop("LLM_BASE_URL", None)
        write_file_config(values)
        self._cache = values

    @property
    def DATABASE_URL(self) -> str | None:
        return self._load().get("DATABASE_URL") or os.getenv("DATABASE_URL")

    @property
    def MEMORY_ENABLED(self) -> bool:
        value = self._load().get("MEMORY_ENABLED", os.getenv("LOBESYNC_MEMORY_ENABLED", "false"))
        return value if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "on"}

    @property
    def LLM_PROVIDER(self) -> str:
        return self._load().get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "anthropic"

    @property
    def LLM_MODEL(self) -> str:
        return (
            self._load().get("LLM_MODEL") or os.getenv("LLM_MODEL") or "claude-haiku-4-5-20251001"
        )

    @property
    def LLM_BASE_URL(self) -> str | None:
        value = self._load().get("LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
        return validate_openai_base_url(value) if value else None

    @property
    def LLM_API_KEY(self) -> str | None:
        file_cfg = self._load()
        return get_api_key(
            self.LLM_PROVIDER,
            allow_environment=self.LLM_PROVIDER != "custom",
        ) or file_cfg.get("LLM_API_KEY") or file_cfg.get("ANTHROPIC_API_KEY")


config = Config()
