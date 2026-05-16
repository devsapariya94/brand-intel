"""Anthropic Claude provider implementation"""
import logging
from typing import List, Optional
import anthropic
from anthropic import AsyncAnthropic
from .base import (
    BaseLLMProvider,
    ChatMessage,
    ChatCompletionResponse,
    LLMConfig,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    TimeoutError as LLMTimeoutError,
    InvalidResponseError
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude implementation with OpenAI-compatible interface.
    Supports Claude 3 models (Haiku, Sonnet, Opus).
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        Call Claude API with OpenAI-compatible interface.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-2)
            **kwargs: Additional Anthropic parameters

        Returns:
            ChatCompletionResponse with standardized format

        Raises:
            LLMProviderError: If API call fails
        """
        try:
            system_message = None
            claude_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            response = await self.client.messages.create(
                model=self.config.model,
                system=system_message,
                messages=claude_messages,
                temperature=temperature or self.config.temperature,
                **kwargs
            )

            content = response.content[0].text if response.content else ""

            self.call_count += 1

            return ChatCompletionResponse(
                id=response.id,
                model=response.model,
                content=content,
                finish_reason=response.stop_reason or "stop",
                provider="anthropic"
            )

        except anthropic.RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            self._record_error(error_msg)
            logger.warning(error_msg)
            raise RateLimitError(error_msg, "anthropic")

        except anthropic.AuthenticationError as e:
            error_msg = f"Authentication failed: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg)
            raise AuthenticationError(error_msg, "anthropic")

        except anthropic.APITimeoutError as e:
            error_msg = f"Request timeout: {str(e)}"
            self._record_error(error_msg)
            logger.warning(error_msg)
            raise LLMTimeoutError(error_msg, "anthropic")

        except anthropic.APIError as e:
            error_msg = f"Anthropic API error: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg)
            raise LLMProviderError(error_msg, "anthropic", retryable=True)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg, exc_info=True)
            raise LLMProviderError(error_msg, "anthropic", retryable=False)

    async def is_available(self) -> bool:
        """
        Check Claude API availability.

        Returns:
            True if API is accessible
        """
        try:
            await self.client.messages.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                timeout=5
            )
            return True
        except Exception as e:
            logger.warning(f"Anthropic availability check failed: {e}")
            return False


# Made with Bob
