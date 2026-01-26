"""LLM provider abstraction for multiple backends."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncIterator

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model identifier."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider - Sonnet 4.5 for best reasoning."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model identifier (default: Sonnet 4.5)
        """
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key)
            self.model = model
            self.logger = logging.getLogger(self.__class__.__name__)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with Claude."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "anthropic"


class MistralProvider(LLMProvider):
    """Mistral provider - Devstral for code generation."""

    def __init__(
        self,
        api_key: str,
        model: str = "devstral-2-123b"
    ):
        """
        Initialize Mistral provider.

        Args:
            api_key: Mistral API key
            model: Model identifier (default: Devstral 2)
        """
        try:
            from mistralai.async_client import MistralAsyncClient
            self.client = MistralAsyncClient(api_key=api_key)
            self.model = model
            self.logger = logging.getLogger(self.__class__.__name__)
        except ImportError:
            raise ImportError("mistralai package not installed. Run: pip install mistralai")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with Mistral."""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Mistral API error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "mistral"


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider - Efficient open-source alternative."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat"
    ):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            model: Model identifier
        """
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            self.model = model
            self.logger = logging.getLogger(self.__class__.__name__)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with DeepSeek."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"DeepSeek API error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "deepseek"


class OpenAIProvider(LLMProvider):
    """OpenAI provider - GPT-4/GPT-4o fallback."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-2024-11-20"
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model identifier
        """
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = model
            self.logger = logging.getLogger(self.__class__.__name__)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "openai"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider - Run models locally without API costs."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434/v1"
    ):
        """
        Initialize Ollama provider for local LLM inference.

        Args:
            model: Model identifier (e.g., llama3.2, codellama, mistral, qwen2.5-coder)
            base_url: Ollama API endpoint (default: http://localhost:11434/v1)
        """
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key="ollama",  # Required but not used by Ollama
                base_url=base_url
            )
            self.model = model
            self.base_url = base_url
            self.logger = logging.getLogger(self.__class__.__name__)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with local Ollama model."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Ollama API error: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "ollama"


class LLMFactory:
    """Factory for creating LLM providers."""

    PROVIDERS = {
        "anthropic": AnthropicProvider,
        "mistral": MistralProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }

    DEFAULT_MODELS = {
        "anthropic": "claude-sonnet-4-5-20250929",
        "mistral": "devstral-2-123b",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-2024-11-20",
        "ollama": "llama3.2",
    }

    @classmethod
    def create(
        cls,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> LLMProvider:
        """
        Create LLM provider instance.

        Args:
            provider: Provider name (anthropic, mistral, deepseek, openai, ollama)
            api_key: API key for the provider (not required for ollama)
            model: Optional model identifier (uses default if not specified)
            base_url: Optional base URL for local providers (ollama)

        Returns:
            LLMProvider instance

        Example:
            >>> llm = LLMFactory.create("anthropic", api_key="sk-...")
            >>> llm = LLMFactory.create("ollama", model="codellama")
            >>> llm = LLMFactory.create("ollama", model="qwen2.5-coder", base_url="http://localhost:11434/v1")
        """
        provider = provider.lower()

        if provider not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls.PROVIDERS.keys())}"
            )

        provider_class = cls.PROVIDERS[provider]
        model = model or cls.DEFAULT_MODELS[provider]

        # Ollama doesn't require API key
        if provider == "ollama":
            if base_url:
                return provider_class(model=model, base_url=base_url)
            return provider_class(model=model)

        if not api_key:
            raise ValueError(f"API key required for provider: {provider}")

        return provider_class(api_key=api_key, model=model)

    @classmethod
    def get_recommended_for_task(cls, task_type: str) -> str:
        """
        Get recommended provider for a task type.

        Args:
            task_type: Task type (reasoning, coding, general)

        Returns:
            Recommended provider name
        """
        recommendations = {
            "reasoning": "anthropic",  # Sonnet 4.5 for complex reasoning
            "coding": "mistral",       # Devstral for code generation
            "general": "deepseek",     # Cost-effective for general tasks
            "coordination": "anthropic",  # Sonnet for orchestration
            "risk": "anthropic",       # Sonnet for nuanced risk decisions
        }

        return recommendations.get(task_type, "anthropic")
