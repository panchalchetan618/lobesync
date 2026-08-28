from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel

from lobesync.config import config

MAX_TOKENS = 4096


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    package: str
    chat_class: str
    key_kwarg: str | None = "api_key"
    max_tokens_kwarg: str = "max_tokens"
    default_model: str = ""
    supports_prompt_caching: bool = False
    extra_kwargs: dict = field(default_factory=dict)

    @property
    def installed(self) -> bool:
        try:
            return importlib.util.find_spec(self.package) is not None
        except (ImportError, ValueError):
            return False


PROVIDERS: dict[str, Provider] = {
    "anthropic": Provider(
        id="anthropic",
        label="Anthropic (Claude)",
        package="langchain_anthropic",
        chat_class="langchain_anthropic.ChatAnthropic",
        key_kwarg="api_key",
        default_model="claude-haiku-4-5-20251001",
        supports_prompt_caching=True,
    ),
    "openai": Provider(
        id="openai",
        label="OpenAI (GPT)",
        package="langchain_openai",
        chat_class="langchain_openai.ChatOpenAI",
        key_kwarg="api_key",
        default_model="gpt-4o-mini",
    ),
    "google": Provider(
        id="google",
        label="Google (Gemini)",
        package="langchain_google_genai",
        chat_class="langchain_google_genai.ChatGoogleGenerativeAI",
        key_kwarg="google_api_key",
        max_tokens_kwarg="max_output_tokens",
        default_model="gemini-2.5-flash",
    ),
    "groq": Provider(
        id="groq",
        label="Groq (fast inference)",
        package="langchain_groq",
        chat_class="langchain_groq.ChatGroq",
        key_kwarg="groq_api_key",
        default_model="llama-3.3-70b-versatile",
    ),
    "mistral": Provider(
        id="mistral",
        label="Mistral AI",
        package="langchain_mistralai",
        chat_class="langchain_mistralai.ChatMistralAI",
        key_kwarg="mistral_api_key",
        default_model="mistral-small-latest",
    ),
    "ollama": Provider(
        id="ollama",
        label="Ollama (local)",
        package="langchain_ollama",
        chat_class="langchain_ollama.ChatOllama",
        key_kwarg=None,
        max_tokens_kwarg="num_predict",
        default_model="llama3.1",
    ),
}


def _resolve_provider(provider_id: str) -> Provider:
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise ValueError(f"Unsupported LLM provider: {provider_id!r}")
    return provider


def get_chat_model(max_tokens: int | None = None) -> BaseChatModel:
    """Build the configured chat model for the active provider."""
    provider = _resolve_provider(config.LLM_PROVIDER)

    module_name, _, class_name = provider.chat_class.rpartition(".")
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            f"Provider '{provider.label}' requires '{provider.package}'. "
            f"Install it with: pip install {provider.package}"
        ) from error
    cls = getattr(module, class_name)

    kwargs: dict = {"model": config.LLM_MODEL}
    kwargs[provider.max_tokens_kwarg] = max_tokens or MAX_TOKENS
    if provider.key_kwarg:
        kwargs[provider.key_kwarg] = config.LLM_API_KEY
    kwargs.update(provider.extra_kwargs)
    return cls(**kwargs)


def get_model_name() -> str:
    return config.LLM_MODEL


def use_prompt_caching() -> bool:
    return _resolve_provider(config.LLM_PROVIDER).supports_prompt_caching
