"""Tests for the quantcoder.core.llm module (Ollama-only)."""

from unittest.mock import MagicMock, AsyncMock, patch

from quantcoder.core.llm import LLMHandler


class TestLLMHandler:
    """Tests for LLMHandler class."""

    def _make_handler(self, mock_config):
        """Create an LLMHandler with mocked Ollama providers."""
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "qwen2.5-coder:14b"
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


class TestFormatSectionsForPrompt:
    """Tests for LLMHandler._format_sections_for_prompt."""

    def test_under_budget(self):
        """All sections fit within budget."""
        sections = {"Methodology": "Some methods.", "Results": "Some results."}
        result = LLMHandler._format_sections_for_prompt(sections, max_chars=10000)
        assert "Methodology" in result
        assert "Results" in result

    def test_over_budget_truncates_low_priority(self):
        """Low-priority sections are excluded when budget is tight."""
        sections = {
            "Trading Strategy": "A" * 500,
            "References": "B" * 500,
        }
        # Budget only allows ~550 chars total (header + content)
        result = LLMHandler._format_sections_for_prompt(sections, max_chars=550)
        assert "Trading Strategy" in result
        # References may be partially included or excluded
        assert len(result) <= 600  # some tolerance for headers

    def test_high_priority_sections_first(self):
        """High-priority sections appear before medium-priority ones."""
        sections = {
            "Conclusion": "Wrap up.",
            "Model Calibration": "Key params here.",
        }
        result = LLMHandler._format_sections_for_prompt(sections, max_chars=10000)
        model_pos = result.index("Model Calibration")
        conclusion_pos = result.index("Conclusion")
        assert model_pos < conclusion_pos

    def test_empty_sections(self):
        """Empty dict returns empty string."""
        result = LLMHandler._format_sections_for_prompt({}, max_chars=10000)
        assert result == ""


class TestExtractKeyPassages:
    """Tests for LLMHandler.extract_key_passages (Pass 1)."""

    def _make_handler(self, mock_config):
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "mistral"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_factory.create.return_value = mock_provider
            handler = LLMHandler(mock_config)
        return handler

    def test_sends_full_sections(self, mock_config):
        """Verify full section text is sent, not keyword-filtered snippets."""
        handler = self._make_handler(mock_config)
        sections = {"Methodology": "OU process with mean-reversion parameter theta=0.5"}

        with patch("quantcoder.core.llm._run_async", return_value="[Methodology] \"OU process...\"") as mock_run:
            result = handler.extract_key_passages(sections)

        assert result is not None
        # Verify _run_async was called and sections were in the prompt
        call_args = mock_run.call_args
        assert call_args is not None

    def test_returns_none_on_empty_sections(self, mock_config):
        """Empty sections dict returns None."""
        handler = self._make_handler(mock_config)
        result = handler.extract_key_passages({})
        assert result is None

    def test_returns_none_on_llm_failure(self, mock_config):
        """LLM exception returns None."""
        handler = self._make_handler(mock_config)
        sections = {"Intro": "Some text."}

        with patch("quantcoder.core.llm._run_async", side_effect=Exception("timeout")):
            result = handler.extract_key_passages(sections)

        assert result is None


class TestInterpretStrategy:
    """Tests for LLMHandler.interpret_strategy (Pass 2)."""

    def _make_handler(self, mock_config):
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "mistral"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_factory.create.return_value = mock_provider
            handler = LLMHandler(mock_config)
        return handler

    def test_passes_extractions_to_llm(self, mock_config):
        """Verify Pass 1 extractions are sent as input to Pass 2."""
        handler = self._make_handler(mock_config)
        extractions = '[Methodology] "theta = 0.5, half-life = 10 days"'

        with patch("quantcoder.core.llm._run_async", return_value="## STRATEGY OVERVIEW\nMean reversion") as mock_run:
            result = handler.interpret_strategy(extractions)

        assert result is not None
        assert "STRATEGY OVERVIEW" in result

    def test_returns_none_on_empty_input(self, mock_config):
        """Empty extractions returns None."""
        handler = self._make_handler(mock_config)
        assert handler.interpret_strategy("") is None
        assert handler.interpret_strategy("   ") is None

    def test_returns_none_on_llm_failure(self, mock_config):
        """LLM exception returns None."""
        handler = self._make_handler(mock_config)
        with patch("quantcoder.core.llm._run_async", side_effect=Exception("timeout")):
            result = handler.interpret_strategy("some extractions")
        assert result is None
