"""LLM provider factory."""

from functools import lru_cache

from app.core.config import LLMProviderType, Settings, get_settings
from app.llm.base import BaseLLMProvider, LLMProviderConfig
from app.llm.providers import (
    DeepSeekProvider,
    GLMProvider,
    MoonshotProvider,
    QwenProvider,
)

_PROVIDER_MAP: dict[LLMProviderType, type[BaseLLMProvider]] = {
    LLMProviderType.DEEPSEEK: DeepSeekProvider,
    LLMProviderType.QWEN: QwenProvider,
    LLMProviderType.GLM: GLMProvider,
    LLMProviderType.MOONSHOT: MoonshotProvider,
}

_API_KEY_MAP: dict[LLMProviderType, str] = {
    LLMProviderType.DEEPSEEK: "DEEPSEEK_API_KEY",
    LLMProviderType.QWEN: "QWEN_API_KEY",
    LLMProviderType.GLM: "GLM_API_KEY",
    LLMProviderType.MOONSHOT: "MOONSHOT_API_KEY",
}

_BASE_URL_MAP: dict[LLMProviderType, str] = {
    LLMProviderType.DEEPSEEK: "DEEPSEEK_BASE_URL",
    LLMProviderType.QWEN: "QWEN_BASE_URL",
    LLMProviderType.GLM: "GLM_BASE_URL",
    LLMProviderType.MOONSHOT: "MOONSHOT_BASE_URL",
}


def create_llm_provider(
    provider_type: LLMProviderType | None = None,
    settings: Settings | None = None,
) -> BaseLLMProvider:
    """Create an LLM provider instance.

    Args:
        provider_type: Which provider to use. Defaults to settings.LLM_PROVIDER.
        settings: Application settings. Defaults to get_settings().

    Returns:
        Configured BaseLLMProvider instance.

    Raises:
        ValueError: If API key is missing for the selected provider.
    """
    settings = settings or get_settings()
    provider_type = provider_type or settings.LLM_PROVIDER

    api_key = getattr(settings, _API_KEY_MAP[provider_type])
    if not api_key:
        raise ValueError(
            f"API key for provider '{provider_type.value}' is not configured. "
            f"Set {_API_KEY_MAP[provider_type]} in your .env file."
        )

    base_url = getattr(settings, _BASE_URL_MAP[provider_type])

    config = LLMProviderConfig(
        api_key=api_key,
        base_url=base_url,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=settings.LLM_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )

    provider_cls = _PROVIDER_MAP[provider_type]
    return provider_cls(config)


@lru_cache()
def get_llm_provider() -> BaseLLMProvider:
    """Get a cached LLM provider instance."""
    return create_llm_provider()
