"""Tests for the quantcoder.core.llm module."""

from unittest.mock import patch

from quantcoder.core.llm import LLMHandler


class TestLLMHandler:
    """Tests for LLMHandler class."""

    def test_init_with_config(self, mock_config, mock_openai_client):
        """Test initialization with config."""
        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)
            assert handler.model == "gpt-4o"
            assert handler.temperature == 0.5

    def test_generate_summary(self, mock_config, mock_openai_client, sample_extracted_data):
        """Test summary generation."""
        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)
            result = handler.generate_summary(sample_extracted_data)

            assert result is not None
            mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_qc_code(self, mock_config, mock_openai_client):
        """Test QuantConnect code generation."""
        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)
            result = handler.generate_qc_code("Test strategy summary")

            assert result is not None
            mock_openai_client.chat.completions.create.assert_called_once()

    def test_extract_code_from_markdown(self, mock_config, mock_openai_client):
        """Test extraction of code from markdown blocks."""
        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)

            markdown_response = """```python
def test():
    pass
```"""
            result = handler._extract_code_from_response(markdown_response)
            assert result == "def test():\n    pass"

    def test_extract_code_without_markdown(self, mock_config, mock_openai_client):
        """Test extraction when response has no markdown."""
        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)

            plain_response = "def test():\n    pass"
            result = handler._extract_code_from_response(plain_response)
            assert result == plain_response

    def test_handles_api_error(self, mock_config, mock_openai_client, sample_extracted_data):
        """Test handling of API errors."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("quantcoder.core.llm.OpenAI", return_value=mock_openai_client):
            handler = LLMHandler(mock_config)
            result = handler.generate_summary(sample_extracted_data)

            assert result is None
