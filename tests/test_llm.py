"""Tests for the quantcoder.core.llm module (Ollama-only)."""

from unittest.mock import MagicMock, AsyncMock, patch

from quantcoder.core.llm import LLMHandler


class TestLLMHandler:
    """Tests for LLMHandler class."""

    def _make_handler(self, mock_config):
        """Create an LLMHandler with mocked Ollama providers."""
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "qwen2.5-coder:32b"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_factory.create.return_value = mock_provider
            handler = LLMHandler(mock_config)
        return handler, mock_provider

    def test_init_with_config(self, mock_config):
        """Test initialization with config."""
        handler, _ = self._make_handler(mock_config)
        assert handler.temperature == 0.5
        assert handler.max_tokens == 1000

    def test_generate_summary(self, mock_config, sample_extracted_data):
        """Test summary generation calls Ollama."""
        handler, mock_provider = self._make_handler(mock_config)

        # Patch _run_async to avoid event loop issues
        with patch("quantcoder.core.llm._run_async", return_value="## INDICATORS\n- RSI"):
            result = handler.generate_summary(sample_extracted_data)

        assert result is not None
        assert "INDICATORS" in result

    def test_generate_qc_code(self, mock_config):
        """Test QuantConnect code generation."""
        handler, mock_provider = self._make_handler(mock_config)

        code = "from AlgorithmImports import *\nclass Test(QCAlgorithm): pass"
        with patch("quantcoder.core.llm._run_async", return_value=code):
            result = handler.generate_qc_code("Test strategy summary")

        assert result is not None
        assert "AlgorithmImports" in result

    def test_generate_qc_code_strips_markdown(self, mock_config):
        """Test markdown code fences are stripped."""
        handler, _ = self._make_handler(mock_config)

        md_response = "```python\ndef test():\n    pass\n```"
        with patch("quantcoder.core.llm._run_async", return_value=md_response):
            result = handler.generate_qc_code("Test")

        assert result == "def test():\n    pass"

    def test_refine_code(self, mock_config):
        """Test code refinement."""
        handler, _ = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", return_value="fixed code"):
            result = handler.refine_code("broken code")

        assert result == "fixed code"

    def test_fix_runtime_error(self, mock_config):
        """Test runtime error fixing."""
        handler, _ = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", return_value="fixed code"):
            result = handler.fix_runtime_error("code", "NameError: x is not defined")

        assert result == "fixed code"

    def test_chat(self, mock_config):
        """Test chat function."""
        handler, _ = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", return_value="Hello!"):
            result = handler.chat("Hi there")

        assert result == "Hello!"

    def test_handles_api_error(self, mock_config, sample_extracted_data):
        """Test handling of API errors returns None."""
        handler, _ = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", side_effect=Exception("Connection refused")):
            result = handler.generate_summary(sample_extracted_data)

        assert result is None

    def test_strip_markdown_python_fence(self):
        """Test static _strip_markdown with python fence."""
        text = "```python\ndef test():\n    pass\n```"
        assert LLMHandler._strip_markdown(text) == "def test():\n    pass"

    def test_strip_markdown_generic_fence(self):
        """Test static _strip_markdown with generic fence."""
        text = "```\ndef test():\n    pass\n```"
        assert LLMHandler._strip_markdown(text) == "def test():\n    pass"

    def test_strip_markdown_no_fence(self):
        """Test static _strip_markdown without fence."""
        text = "def test():\n    pass"
        assert LLMHandler._strip_markdown(text) == text
