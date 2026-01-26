"""Tests for the quantcoder.llm.providers module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantcoder.llm.providers import (
    LLMProvider,
    AnthropicProvider,
    MistralProvider,
    DeepSeekProvider,
    OpenAIProvider,
    OllamaProvider,
    LLMFactory,
)


class TestLLMFactory:
    """Tests for LLMFactory class."""

    def test_providers_registered(self):
        """Test all providers are registered."""
        providers = LLMFactory.PROVIDERS
        assert "anthropic" in providers
        assert "mistral" in providers
        assert "deepseek" in providers
        assert "openai" in providers
        assert "ollama" in providers

    def test_default_models_defined(self):
        """Test default models are defined for all providers."""
        for provider in LLMFactory.PROVIDERS.keys():
            assert provider in LLMFactory.DEFAULT_MODELS

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("unknown_provider", api_key="test")
        assert "Unknown provider" in str(exc_info.value)

    def test_create_without_api_key(self):
        """Test creating provider without API key raises error."""
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("anthropic")
        assert "API key required" in str(exc_info.value)

    @patch('quantcoder.llm.providers.OllamaProvider.__init__', return_value=None)
    def test_create_ollama_without_api_key(self, mock_init):
        """Test Ollama can be created without API key."""
        # Ollama doesn't require API key
        result = LLMFactory.create("ollama")
        mock_init.assert_called_once()

    @patch('quantcoder.llm.providers.OllamaProvider.__init__', return_value=None)
    def test_create_ollama_with_custom_url(self, mock_init):
        """Test Ollama with custom base URL."""
        LLMFactory.create("ollama", base_url="http://custom:11434/v1")
        mock_init.assert_called_with(model="llama3.2", base_url="http://custom:11434/v1")

    @patch('quantcoder.llm.providers.AnthropicProvider.__init__', return_value=None)
    def test_create_anthropic(self, mock_init):
        """Test creating Anthropic provider."""
        LLMFactory.create("anthropic", api_key="test-key")
        mock_init.assert_called_with(
            api_key="test-key",
            model="claude-sonnet-4-5-20250929"
        )

    @patch('quantcoder.llm.providers.AnthropicProvider.__init__', return_value=None)
    def test_create_with_custom_model(self, mock_init):
        """Test creating provider with custom model."""
        LLMFactory.create("anthropic", api_key="key", model="claude-3-opus")
        mock_init.assert_called_with(api_key="key", model="claude-3-opus")

    def test_get_recommended_for_reasoning(self):
        """Test recommended provider for reasoning."""
        assert LLMFactory.get_recommended_for_task("reasoning") == "anthropic"

    def test_get_recommended_for_coding(self):
        """Test recommended provider for coding."""
        assert LLMFactory.get_recommended_for_task("coding") == "mistral"

    def test_get_recommended_for_general(self):
        """Test recommended provider for general tasks."""
        assert LLMFactory.get_recommended_for_task("general") == "deepseek"

    def test_get_recommended_unknown_task(self):
        """Test recommended provider for unknown task defaults to anthropic."""
        assert LLMFactory.get_recommended_for_task("unknown") == "anthropic"


class TestAnthropicProvider:
    """Tests for AnthropicProvider class."""

    @patch('anthropic.AsyncAnthropic')
    def test_init(self, mock_client_class):
        """Test provider initialization."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.model == "claude-sonnet-4-5-20250929"
        assert provider.get_provider_name() == "anthropic"

    @patch('anthropic.AsyncAnthropic')
    def test_init_custom_model(self, mock_client_class):
        """Test provider with custom model."""
        provider = AnthropicProvider(api_key="key", model="claude-3-opus")
        assert provider.model == "claude-3-opus"
        assert provider.get_model_name() == "claude-3-opus"

    @patch('anthropic.AsyncAnthropic')
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_client_class):
        """Test successful chat completion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello from Claude")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(api_key="test-key")
        result = await provider.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "Hello from Claude"
        mock_client.messages.create.assert_called_once()

    @patch('anthropic.AsyncAnthropic')
    @pytest.mark.asyncio
    async def test_chat_error(self, mock_client_class):
        """Test chat error handling."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API Error"))
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(api_key="test-key")

        with pytest.raises(Exception) as exc_info:
            await provider.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "API Error" in str(exc_info.value)


class TestMistralProvider:
    """Tests for MistralProvider class."""

    @patch('mistralai.async_client.MistralAsyncClient')
    def test_init(self, mock_client_class):
        """Test provider initialization."""
        provider = MistralProvider(api_key="test-key")
        assert provider.model == "devstral-2-123b"
        assert provider.get_provider_name() == "mistral"

    @patch('mistralai.async_client.MistralAsyncClient')
    def test_get_model_name(self, mock_client_class):
        """Test get_model_name method."""
        provider = MistralProvider(api_key="key", model="custom-model")
        assert provider.get_model_name() == "custom-model"

    @patch('mistralai.async_client.MistralAsyncClient')
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_client_class):
        """Test successful chat completion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mistral response"))]
        mock_client.chat = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = MistralProvider(api_key="test-key")
        result = await provider.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "Mistral response"


class TestDeepSeekProvider:
    """Tests for DeepSeekProvider class."""

    @patch('openai.AsyncOpenAI')
    def test_init(self, mock_client_class):
        """Test provider initialization with DeepSeek base URL."""
        provider = DeepSeekProvider(api_key="test-key")
        assert provider.model == "deepseek-chat"
        assert provider.get_provider_name() == "deepseek"
        mock_client_class.assert_called_with(
            api_key="test-key",
            base_url="https://api.deepseek.com"
        )

    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_client_class):
        """Test successful chat completion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="DeepSeek response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = DeepSeekProvider(api_key="test-key")
        result = await provider.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "DeepSeek response"


class TestOpenAIProvider:
    """Tests for OpenAIProvider class."""

    @patch('openai.AsyncOpenAI')
    def test_init(self, mock_client_class):
        """Test provider initialization."""
        provider = OpenAIProvider(api_key="test-key")
        assert provider.model == "gpt-4o-2024-11-20"
        assert provider.get_provider_name() == "openai"

    @patch('openai.AsyncOpenAI')
    def test_custom_model(self, mock_client_class):
        """Test provider with custom model."""
        provider = OpenAIProvider(api_key="key", model="gpt-4-turbo")
        assert provider.get_model_name() == "gpt-4-turbo"

    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_client_class):
        """Test successful chat completion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OpenAI response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        result = await provider.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "OpenAI response"

    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_error(self, mock_client_class):
        """Test chat error handling."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("Rate limit"))
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")

        with pytest.raises(Exception) as exc_info:
            await provider.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "Rate limit" in str(exc_info.value)


class TestOllamaProvider:
    """Tests for OllamaProvider class."""

    @patch('openai.AsyncOpenAI')
    def test_init_defaults(self, mock_client_class):
        """Test provider initialization with defaults."""
        provider = OllamaProvider()
        assert provider.model == "llama3.2"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.get_provider_name() == "ollama"
        mock_client_class.assert_called_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1"
        )

    @patch('openai.AsyncOpenAI')
    def test_init_custom_config(self, mock_client_class):
        """Test provider with custom configuration."""
        provider = OllamaProvider(
            model="codellama",
            base_url="http://192.168.1.100:11434/v1"
        )
        assert provider.model == "codellama"
        assert provider.get_model_name() == "codellama"

    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_success(self, mock_client_class):
        """Test successful chat completion with local Ollama."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Ollama response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        provider = OllamaProvider()
        result = await provider.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )

        assert result == "Ollama response"

    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_connection_error(self, mock_client_class):
        """Test chat error when Ollama is not running."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_client_class.return_value = mock_client

        provider = OllamaProvider()

        with pytest.raises(Exception) as exc_info:
            await provider.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "Connection refused" in str(exc_info.value)
