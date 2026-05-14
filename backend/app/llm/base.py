"""Base LLM provider interface and shared types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class LLMUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from a non-streaming LLM call."""

    content: str
    model: str
    usage: LLMUsage
    finish_reason: str = "stop"
    latency_ms: float = 0.0


@dataclass
class LLMStreamResponse:
    """A single chunk from a streaming LLM call."""

    delta: str
    finish_reason: str | None = None


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""

    api_key: str
    base_url: str
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    All providers must implement:
    - chat: non-streaming completion
    - stream_chat: streaming completion
    - get_model_name: return the current model identifier
    """

    def __init__(self, config: LLMProviderConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Send a non-streaming chat completion request.

        Args:
            messages: Conversation messages.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            response_format: Optional JSON mode specification.

        Returns:
            LLMResponse with content, usage, and metadata.
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamResponse]:
        """Send a streaming chat completion request.

        Args:
            messages: Conversation messages.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Yields:
            LLMStreamResponse chunks as they arrive.
        """
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the current model identifier string."""
        ...

    def _build_messages(
        self,
        system_prompt: str | None,
        user_message: str,
        history: list[LLMMessage] | None = None,
    ) -> list[LLMMessage]:
        """Helper to build a standard message list."""
        messages: list[LLMMessage] = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        if history:
            messages.extend(history)
        messages.append(LLMMessage(role=MessageRole.USER, content=user_message))
        return messages
