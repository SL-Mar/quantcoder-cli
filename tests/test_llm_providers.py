"""Tests for the quantcoder.llm.providers module (Ollama-only)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantcoder.llm.providers import (
    LLMProvider,
    OllamaProvider,
    LLMFactory,
    TASK_MODELS,
)


class TestLLMFactory:
    """Tests for LLMFactory task-based routing."""

    def test_create_coding_task(self):
        """Test coding task routes to qwen2.5-coder:14b."""
        provider = LLMFactory.create(task="coding")
        assert isinstance(provider, OllamaProvider)
        assert provider.get_model_name() == "qwen2.5-coder:14b"

    def test_create_reasoning_task(self):
        """Test reasoning task routes to mistral."""
        provider = LLMFactory.create(task="reasoning")
        assert isinstance(provider, OllamaProvider)
        assert provider.get_model_name() == "mistral"

    def test_create_chat_task(self):
        """Test chat task routes to mistral."""
        provider = LLMFactory.create(task="chat")
        assert provider.get_model_name() == "mistral"

    def test_create_summary_task(self):
        """Test summary task routes to mistral."""
        provider = LLMFactory.create(task="summary")
        assert provider.get_model_name() == "mistral"

    def test_create_code_generation_task(self):
        """Test code_generation task routes to qwen2.5-coder:14b."""
        provider = LLMFactory.create(task="code_generation")
        assert provider.get_model_name() == "qwen2.5-coder:14b"

    def test_create_unknown_task_defaults_to_coder(self):
        """Test unknown task defaults to qwen2.5-coder:14b."""
        provider = LLMFactory.create(task="some_unknown_task")
        assert provider.get_model_name() == "qwen2.5-coder:14b"

    def test_create_with_model_override(self):
        """Test model override takes precedence."""
        provider = LLMFactory.create(task="coding", model="codellama:13b")
        assert provider.get_model_name() == "codellama:13b"

    def test_create_with_custom_url(self):
        """Test custom base URL is passed through."""
        provider = LLMFactory.create(task="coding", base_url="http://remote:11434")
        assert provider.base_url == "http://remote:11434"

    def test_create_with_custom_timeout(self):
        """Test custom timeout is set."""
        provider = LLMFactory.create(task="coding", timeout=120)
        assert provider.timeout == 120

    def test_all_task_models_defined(self):
        """Test all task mappings resolve to valid models."""
        for task, model in TASK_MODELS.items():
            assert isinstance(model, str)
            assert len(model) > 0

    def test_provider_is_always_ollama(self):
        """Test factory always returns OllamaProvider."""
        for task in TASK_MODELS:
            provider = LLMFactory.create(task=task)
            assert provider.get_provider_name() == "ollama"


class TestOllamaProvider:
    """Tests for OllamaProvider class."""

    def test_init_defaults(self):
        """Test provider initialization with new defaults."""
        provider = OllamaProvider()
        assert provider.model == "qwen2.5-coder:14b"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 600
        assert provider.get_provider_name() == "ollama"

    def test_init_custom_config(self):
        """Test provider with custom configuration."""
        provider = OllamaProvider(
            model="mistral",
            base_url="http://10.0.0.50:11434",
            timeout=300
        )
        assert provider.model == "mistral"
        assert provider.get_model_name() == "mistral"
        assert provider.base_url == "http://10.0.0.50:11434"
        assert provider.timeout == 300

    def test_init_strips_v1_suffix(self):
        """Test /v1 suffix is stripped from base URL."""
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        assert provider.base_url == "http://localhost:11434"

    def test_init_with_env_base_url(self, monkeypatch):
        """Test provider uses OLLAMA_BASE_URL env var."""
        monkeypatch.setenv('OLLAMA_BASE_URL', 'http://custom:11434')
        provider = OllamaProvider()
        assert provider.base_url == 'http://custom:11434'

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat completion with local Ollama."""
        provider = OllamaProvider()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={
                "message": {"content": "  Ollama response  "}
            })

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock()

            result = await provider.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )

            assert result == "Ollama response"

    @pytest.mark.asyncio
    async def test_chat_fallback_response_format(self):
        """Test chat handles alternative response format."""
        provider = OllamaProvider()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={
                "response": "Alternative format response"
            })

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock()

            result = await provider.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )

            assert result == "Alternative format response"

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test health check returns True when server is available."""
        provider = OllamaProvider()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200

            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock()

            result = await provider.check_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check returns False when server is unavailable."""
        provider = OllamaProvider()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session_class.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_session_class.return_value.__aexit__ = AsyncMock()

            result = await provider.check_health()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models."""
        provider = OllamaProvider()

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={
                "models": [
                    {"name": "qwen2.5-coder:14b"},
                    {"name": "mistral"},
                ]
            })

            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock()

            models = await provider.list_models()
            assert "qwen2.5-coder:14b" in models
            assert "mistral" in models

    def test_is_llm_provider_subclass(self):
        """Test OllamaProvider is a proper LLMProvider subclass."""
        assert issubclass(OllamaProvider, LLMProvider)
