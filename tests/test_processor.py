"""Tests for the quantcoder.core.processor module."""

import pytest
from unittest.mock import MagicMock, patch

from quantcoder.core.processor import (
    TextPreprocessor,
    CodeValidator,
    KeywordAnalyzer,
    SectionSplitter,
)


class TestTextPreprocessor:
    """Tests for TextPreprocessor class."""

    def test_preprocess_removes_urls(self):
        """Test that URLs are removed from text."""
        preprocessor = TextPreprocessor()
        text = "Visit https://example.com for more info"
        result = preprocessor.preprocess_text(text)
        assert "https://example.com" not in result

    def test_preprocess_removes_electronic_copy_phrase(self):
        """Test that 'Electronic copy available at' phrases are removed."""
        preprocessor = TextPreprocessor()
        text = "Some text Electronic copy available at: ssrn.com more text"
        result = preprocessor.preprocess_text(text)
        assert "Electronic copy available at" not in result

    def test_preprocess_collapses_multiple_newlines(self):
        """Test that multiple newlines are collapsed to single newlines."""
        preprocessor = TextPreprocessor()
        text = "Line 1\n\n\n\nLine 2"
        result = preprocessor.preprocess_text(text)
        assert "\n\n" not in result

    def test_preprocess_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        preprocessor = TextPreprocessor()
        text = "   Some text   "
        result = preprocessor.preprocess_text(text)
        assert result == "Some text"


class TestSectionSplitter:
    """Tests for SectionSplitter class."""

    def test_split_with_headings(self):
        """Test splitting text with detected headings."""
        splitter = SectionSplitter()
        text = "Introduction\nThis is intro.\nMethods\nThis is methods."
        headings = ["Introduction", "Methods"]
        sections = splitter.split_into_sections(text, headings)

        assert "Introduction" in sections
        assert "Methods" in sections
        assert "intro" in sections["Introduction"].lower()
        assert "methods" in sections["Methods"].lower()

    def test_split_without_headings(self):
        """Test splitting text when no headings are detected."""
        splitter = SectionSplitter()
        text = "This is all introduction text."
        headings = []
        sections = splitter.split_into_sections(text, headings)

        assert "Introduction" in sections  # Default section


class TestKeywordAnalyzer:
    """Tests for KeywordAnalyzer class."""

    def test_detects_trading_signals(self):
        """Test detection of trading signal keywords."""
        analyzer = KeywordAnalyzer()
        sections = {"Strategy": "Buy when the trend is up. Sell when RSI is high."}
        result = analyzer.keyword_analysis(sections)

        assert "trading_signal" in result
        assert len(result["trading_signal"]) > 0

    def test_detects_risk_management(self):
        """Test detection of risk management keywords."""
        analyzer = KeywordAnalyzer()
        sections = {"Risk": "Limit drawdown to 10%. Reduce volatility exposure."}
        result = analyzer.keyword_analysis(sections)

        assert "risk_management" in result
        assert len(result["risk_management"]) > 0

    def test_skips_irrelevant_patterns(self):
        """Test that irrelevant patterns are skipped."""
        analyzer = KeywordAnalyzer()
        sections = {"Figures": "See figure 1 for buy signal details."}
        result = analyzer.keyword_analysis(sections)

        # Should not include sentences with "figure X" pattern
        for sentence in result.get("trading_signal", []):
            assert "figure 1" not in sentence.lower()


class TestCodeValidator:
    """Tests for CodeValidator class."""

    def test_validates_correct_code(self, sample_python_code):
        """Test validation of syntactically correct code."""
        validator = CodeValidator()
        assert validator.validate_code(sample_python_code) is True

    def test_rejects_invalid_code(self, invalid_python_code):
        """Test rejection of syntactically invalid code."""
        validator = CodeValidator()
        assert validator.validate_code(invalid_python_code) is False

    def test_handles_empty_code(self):
        """Test handling of empty code string."""
        validator = CodeValidator()
        # Empty string is valid Python
        assert validator.validate_code("") is True

    def test_handles_simple_expression(self):
        """Test validation of simple expressions."""
        validator = CodeValidator()
        assert validator.validate_code("x = 1 + 2") is True
