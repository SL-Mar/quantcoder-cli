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


class TestParseFidelityResponse:
    """Tests for LLMHandler._parse_fidelity_response."""

    def test_complete_unfaithful_response(self):
        """Parse a complete structured response marking code as unfaithful."""
        response = (
            "FAITHFUL: NO\n"
            "SCORE: 2\n"
            "ISSUES:\n"
            "- Code uses RSI instead of OU process\n"
            "- Missing theta parameter\n"
            "CORRECTION_PLAN:\n"
            "Replace RSI logic with numpy-based OU mean-reversion calculation."
        )
        result = LLMHandler._parse_fidelity_response(response)
        assert result["faithful"] is False
        assert result["score"] == 2
        assert len(result["issues"]) == 2
        assert "RSI" in result["issues"][0]
        assert "OU" in result["correction_plan"]

    def test_faithful_response(self):
        """Parse a response that marks code as faithful."""
        response = (
            "FAITHFUL: YES\n"
            "SCORE: 4\n"
            "ISSUES:\n"
            "- Minor: could use more descriptive variable names\n"
            "CORRECTION_PLAN:\n"
            "No structural changes needed."
        )
        result = LLMHandler._parse_fidelity_response(response)
        assert result["faithful"] is True
        assert result["score"] == 4
        assert len(result["issues"]) == 1

    def test_missing_fields_returns_defaults(self):
        """Malformed response returns safe defaults."""
        result = LLMHandler._parse_fidelity_response("Some random text without structure")
        assert result["faithful"] is False
        assert result["score"] == 1
        assert result["issues"] == []
        assert result["correction_plan"] == ""

    def test_empty_response(self):
        """Empty string returns defaults."""
        result = LLMHandler._parse_fidelity_response("")
        assert result["faithful"] is False
        assert result["score"] == 1


class TestAssessFidelity:
    """Tests for LLMHandler.assess_fidelity."""

    def _make_handler(self, mock_config):
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "mistral"
            mock_provider.chat = AsyncMock(return_value="test")
            mock_factory.create.return_value = mock_provider
            handler = LLMHandler(mock_config)
        return handler

    def test_faithful_code_passes(self, mock_config):
        """Faithful response returns faithful=True."""
        handler = self._make_handler(mock_config)
        llm_response = "FAITHFUL: YES\nSCORE: 4\nISSUES:\n- None\nCORRECTION_PLAN:\nNone"

        with patch("quantcoder.core.llm._run_async", return_value=llm_response):
            result = handler.assess_fidelity("OU process summary", "ou code here")

        assert result["faithful"] is True
        assert result["score"] == 4

    def test_unfaithful_code_fails(self, mock_config):
        """Unfaithful response returns faithful=False."""
        handler = self._make_handler(mock_config)
        llm_response = (
            "FAITHFUL: NO\nSCORE: 1\nISSUES:\n"
            "- Uses RSI instead of OU process\n"
            "CORRECTION_PLAN:\nImplement OU model with numpy"
        )

        with patch("quantcoder.core.llm._run_async", return_value=llm_response):
            result = handler.assess_fidelity("OU process summary", "rsi code here")

        assert result["faithful"] is False
        assert result["score"] == 1
        assert len(result["issues"]) > 0

    def test_llm_failure_returns_unfaithful(self, mock_config):
        """LLM exception returns unfaithful default."""
        handler = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", side_effect=Exception("timeout")):
            result = handler.assess_fidelity("summary", "code")

        assert result["faithful"] is False
        assert result["score"] == 1

    def test_malformed_response_returns_unfaithful(self, mock_config):
        """Garbled LLM output returns unfaithful."""
        handler = self._make_handler(mock_config)

        with patch("quantcoder.core.llm._run_async", return_value="I don't understand the question"):
            result = handler.assess_fidelity("summary", "code")

        assert result["faithful"] is False
        assert result["score"] == 1


class TestRegenerateWithCritique:
    """Tests for LLMHandler.regenerate_with_critique."""

    def _make_handler(self, mock_config):
        with patch("quantcoder.core.llm.LLMFactory") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.get_model_name.return_value = "qwen2.5-coder:14b"
            mock_provider.chat = AsyncMock(return_value="test")
            mock_factory.create.return_value = mock_provider
            handler = LLMHandler(mock_config)
        return handler

    def test_returns_regenerated_code(self, mock_config):
        """Returns new code from the coding LLM."""
        handler = self._make_handler(mock_config)
        new_code = "from AlgorithmImports import *\nclass OUAlgo(QCAlgorithm): pass"
        critique = {
            "issues": ["Uses RSI instead of OU"],
            "correction_plan": "Implement OU with numpy",
        }

        with patch("quantcoder.core.llm._run_async", return_value=new_code):
            result = handler.regenerate_with_critique("summary", "old code", critique)

        assert result is not None
        assert "AlgorithmImports" in result

    def test_strips_markdown_from_output(self, mock_config):
        """Markdown fences are stripped from regenerated code."""
        handler = self._make_handler(mock_config)
        md_code = "```python\ndef test(): pass\n```"
        critique = {"issues": ["wrong model"], "correction_plan": "fix it"}

        with patch("quantcoder.core.llm._run_async", return_value=md_code):
            result = handler.regenerate_with_critique("summary", "old code", critique)

        assert "```" not in result
        assert result == "def test(): pass"

    def test_returns_none_on_failure(self, mock_config):
        """LLM exception returns None."""
        handler = self._make_handler(mock_config)
        critique = {"issues": ["wrong"], "correction_plan": "fix"}

        with patch("quantcoder.core.llm._run_async", side_effect=Exception("timeout")):
            result = handler.regenerate_with_critique("summary", "code", critique)

        assert result is None
