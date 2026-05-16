"""Base LLM provider interface following OpenAI API specification"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    """OpenAI-compatible message format"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format"""
        msg = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        return msg


@dataclass
class ChatCompletionResponse:
    """OpenAI-compatible response format"""
    id: str
    model: str
    content: str
    finish_reason: str
    provider: str
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class LLMConfig:
    """Provider configuration"""
    api_key: Optional[str]
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    timeout: int = 30
    enabled: bool = True


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Follows OpenAI API specification for compatibility.

    All providers must implement this interface to ensure
    seamless switching between different LLM services.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.call_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        Generate chat completion following OpenAI format.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-2)
            **kwargs: Provider-specific parameters

        Returns:
            ChatCompletionResponse with standardized format

        Raises:
            LLMProviderError: If API call fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available and healthy.

        Returns:
            True if provider can accept requests
        """
        pass

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get provider usage statistics"""
        return {
            "provider": self.config.base_url or "unknown",
            "model": self.config.model,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "enabled": self.config.enabled
        }

    def _record_error(self, error: str):
        """Record error for monitoring"""
        self.error_count += 1
        self.last_error = error


class LLMProviderError(Exception):
    """Base exception for LLM provider errors"""
    def __init__(self, message: str, provider: str, retryable: bool = True):
        self.message = message
        self.provider = provider
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class RateLimitError(LLMProviderError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, provider: str, retry_after: Optional[int] = None):
        super().__init__(message, provider, retryable=True)
        self.retry_after = retry_after


class AuthenticationError(LLMProviderError):
    """Authentication/API key error"""
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retryable=False)


class TimeoutError(LLMProviderError):
    """Request timeout error"""
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retryable=True)


class InvalidResponseError(LLMProviderError):
    """Invalid or malformed response error"""
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retryable=False)

# Made with Bob
