"""Concrete LLM provider implementations.

All providers use the OpenAI-compatible API format since
DeepSeek, Qwen, GLM, and Moonshot all expose OpenAI-compatible endpoints.
"""

import time
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.core.exceptions import LLMProviderError
from app.llm.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMProviderConfig,
    LLMResponse,
    LLMStreamResponse,
    LLMUsage,
)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Base provider for OpenAI-compatible API endpoints.

    Used by DeepSeek, Qwen, GLM, and Moonshot since they all
    expose OpenAI-compatible chat completion endpoints.
    """

    provider_name: str = "openai-compatible"

    def __init__(self, config: LLMProviderConfig):
        super().__init__(config)
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        start_time = time.monotonic()
        try:
            kwargs: dict = {
                "model": self.config.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await self._client.chat.completions.create(**kwargs)

            latency_ms = (time.monotonic() - start_time) * 1000
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                ),
                finish_reason=choice.finish_reason or "stop",
                latency_ms=latency_ms,
            )
        except Exception as e:
            raise LLMProviderError(
                provider=self.provider_name,
                message=str(e),
                details={"model": self.config.model},
            ) from e

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamResponse]:
        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[m.to_dict() for m in messages],
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMStreamResponse(
                        delta=chunk.choices[0].delta.content,
                        finish_reason=chunk.choices[0].finish_reason,
                    )
        except Exception as e:
            raise LLMProviderError(
                provider=self.provider_name,
                message=str(e),
                details={"model": self.config.model},
            ) from e

    def get_model_name(self) -> str:
        return self.config.model


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API provider."""

    provider_name = "deepseek"


class QwenProvider(OpenAICompatibleProvider):
    """Alibaba Qwen API provider (DashScope compatible mode)."""

    provider_name = "qwen"


class GLMProvider(OpenAICompatibleProvider):
    """Zhipu GLM API provider."""

    provider_name = "glm"


class MoonshotProvider(OpenAICompatibleProvider):
    """Moonshot (Kimi) API provider."""

    provider_name = "moonshot"
