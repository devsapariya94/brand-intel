"""Generic LLM provider implementation using OpenAI API specification"""
import logging
from typing import List, Optional
from urllib.parse import urlparse
import openai
from openai import AsyncOpenAI
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


class GenericLLMProvider(BaseLLMProvider):
    """
    Generic LLM provider using OpenAI API specification.
    Works with any OpenAI-compatible endpoint:
    - OpenAI (https://api.openai.com/v1)
    - Ollama (http://localhost:11434/v1)
    - OpenRouter (https://openrouter.ai/api/v1)
    - Gemini (https://generativelanguage.googleapis.com/v1beta/openai/)
    - Azure OpenAI, and more
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key or "no-key-required",
            base_url=config.base_url,
            timeout=config.timeout
        )

    def _get_provider_name(self) -> str:
        """Extract provider name from base_url"""
        if not self.config.base_url:
            return "openai"
        try:
            parsed = urlparse(self.config.base_url)
            return parsed.hostname or parsed.netloc
        except Exception:
            return self.config.base_url

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        Call Chat Completion API using OpenAI specification.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters

        Returns:
            ChatCompletionResponse with standardized format

        Raises:
            LLMProviderError: If API call fails
        """
        provider_name = self._get_provider_name()

        try:
            openai_messages = [msg.to_dict() for msg in messages]

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                temperature=temperature or self.config.temperature,
                **kwargs
            )

            choice = response.choices[0]

            self.call_count += 1

            return ChatCompletionResponse(
                id=response.id,
                model=response.model,
                content=choice.message.content,
                finish_reason=choice.finish_reason,
                provider=provider_name
            )

        except openai.AuthenticationError as e:
            error_msg = f"Authentication failed: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg)
            raise AuthenticationError(error_msg, provider_name)

        except openai.RateLimitError as e:
            error_msg = f"Rate limit exceeded: {str(e)}"
            self._record_error(error_msg)
            logger.warning(error_msg)
            retry_after = getattr(e, 'retry_after', None)
            raise RateLimitError(error_msg, provider_name, retry_after)

        except openai.APITimeoutError as e:
            error_msg = f"Request timeout: {str(e)}"
            self._record_error(error_msg)
            logger.warning(error_msg)
            raise LLMTimeoutError(error_msg, provider_name)

        except openai.APIError as e:
            error_msg = f"API error: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg)
            raise LLMProviderError(error_msg, provider_name, retryable=True)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self._record_error(error_msg)
            logger.error(error_msg, exc_info=True)
            raise LLMProviderError(error_msg, provider_name, retryable=False)

    async def is_available(self) -> bool:
        """
        Check provider availability.
        Tries models.list() first, falls back to minimal chat completion.

        Returns:
            True if API is accessible
        """
        try:
            await self.client.models.list()
            return True
        except Exception:
            try:
                await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                return True
            except Exception as e:
                logger.warning(f"Provider availability check failed: {e}")
                return False


# Made with Bob
