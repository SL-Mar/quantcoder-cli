"""LLM provider abstraction — Ollama-only local models."""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

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


class OllamaProvider(LLMProvider):
    """Ollama provider — local LLM inference without API keys."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:14b",
        base_url: str = None,
        timeout: int = 600
    ):
        self.model = model
        self.base_url = (base_url or os.environ.get(
            'OLLAMA_BASE_URL', 'http://localhost:11434'
        )).rstrip('/')
        # Strip /v1 suffix if present (common misconfiguration)
        if self.base_url.endswith('/v1'):
            self.base_url = self.base_url[:-3]
        self.timeout = timeout
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")
        self.logger.info(f"Initialized OllamaProvider: {self.base_url}, model={self.model}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """Generate chat completion with Ollama."""
        import aiohttp

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()

                    if 'message' in result and 'content' in result['message']:
                        text = result['message']['content']
                    elif 'response' in result:
                        text = result['response']
                    else:
                        raise ValueError(f"Unexpected response format: {list(result.keys())}")

                    self.logger.info(f"Ollama response received ({len(text)} chars)")
                    return text.strip()

        except aiohttp.ClientConnectorError as e:
            error_msg = (
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Error: {e}"
            )
            self.logger.error(error_msg)
            raise ConnectionError(error_msg) from e
        except aiohttp.ClientResponseError as e:
            error_msg = f"Ollama API error: {e.status} - {e.message}"
            self.logger.error(error_msg)
            raise
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
            raise

    async def check_health(self) -> bool:
        """Check if Ollama server is reachable."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """List available models on the Ollama server."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return [m['name'] for m in data.get('models', [])]
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "ollama"


# Task-to-model mapping
TASK_MODELS = {
    "coding": "qwen2.5-coder:14b",
    "code_generation": "qwen2.5-coder:14b",
    "refinement": "qwen2.5-coder:14b",
    "error_fixing": "qwen2.5-coder:14b",
    "reasoning": "mistral",
    "chat": "mistral",
    "summary": "mistral",
    "coordination": "mistral",
}


class LLMFactory:
    """Factory for creating Ollama LLM providers with task-based model routing."""

    @classmethod
    def create(
        cls,
        task: str = "coding",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 600,
    ) -> OllamaProvider:
        """
        Create an OllamaProvider configured for a specific task.

        Args:
            task: Task type — determines default model.
                  coding/code_generation/refinement/error_fixing → qwen2.5-coder:14b
                  reasoning/chat/summary/coordination → mistral
            model: Override model (uses task default if None)
            base_url: Ollama server URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 600)

        Returns:
            OllamaProvider instance

        Example:
            >>> llm = LLMFactory.create(task="coding")
            >>> llm = LLMFactory.create(task="reasoning", model="mistral")
        """
        resolved_model = model or TASK_MODELS.get(task, "qwen2.5-coder:14b")

        kwargs = {"model": resolved_model, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url

        return OllamaProvider(**kwargs)
