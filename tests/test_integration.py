"""
Integration tests for ArticleProcessor with backend adapter.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from quantcli.processor import ArticleProcessor, OpenAIHandler
from quantcli.backend import OllamaAdapter


class TestArticleProcessorIntegration:
    """Integration tests for ArticleProcessor with backend."""
    
    @patch('spacy.load')  # Mock SpaCy loading
    @patch('quantcli.processor.make_backend')  # Patch where it's imported
    def test_article_processor_initialization_with_backend(self, mock_make_backend, mock_spacy_load):
        """Test that ArticleProcessor initializes with backend from factory."""
        mock_backend = Mock(spec=OllamaAdapter)
        mock_make_backend.return_value = mock_backend
        mock_spacy_load.return_value = Mock()  # Mock SpaCy model
        
        processor = ArticleProcessor()
        
        # Verify backend factory was called
        mock_make_backend.assert_called_once()
        
        # Verify OpenAIHandler has the backend
        assert processor.openai_handler is not None
        assert processor.openai_handler.backend == mock_backend
    
    @patch('spacy.load')  # Mock SpaCy loading
    @patch('quantcli.processor.make_backend')  # Patch where it's imported
    def test_article_processor_handles_backend_creation_failure(self, mock_make_backend, mock_spacy_load):
        """Test that ArticleProcessor handles backend creation failures gracefully."""
        mock_make_backend.side_effect = Exception("Backend creation failed")
        mock_spacy_load.return_value = Mock()  # Mock SpaCy model
        
        processor = ArticleProcessor()
        
        # Processor should still initialize but without handler
        assert processor.openai_handler is None
        assert processor.code_refiner is None
    
    @patch('quantcli.backend_factory.make_backend')
    def test_openai_handler_generate_summary_uses_backend(self, mock_make_backend):
        """Test that OpenAIHandler.generate_summary uses backend.chat_complete."""
        mock_backend = Mock(spec=OllamaAdapter)
        mock_backend.chat_complete.return_value = "This is a generated summary."
        mock_make_backend.return_value = mock_backend
        
        handler = OpenAIHandler(backend=mock_backend)
        extracted_data = {
            'trading_signal': ['Buy when RSI < 30'],
            'risk_management': ['Stop loss at 2%']
        }
        
        summary = handler.generate_summary(extracted_data)
        
        # Verify backend was called
        mock_backend.chat_complete.assert_called_once()
        call_args = mock_backend.chat_complete.call_args
        
        # Check that messages were passed
        messages = call_args[0][0]
        assert isinstance(messages, list)
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        
        # Check that summary was returned
        assert summary == "This is a generated summary."
    
    @patch('quantcli.backend_factory.make_backend')
    def test_openai_handler_generate_qc_code_uses_backend(self, mock_make_backend):
        """Test that OpenAIHandler.generate_qc_code uses backend.chat_complete."""
        mock_backend = Mock(spec=OllamaAdapter)
        mock_backend.chat_complete.return_value = "class MyAlgorithm:\n    pass"
        mock_make_backend.return_value = mock_backend
        
        handler = OpenAIHandler(backend=mock_backend)
        summary = "Trading strategy summary"
        
        code = handler.generate_qc_code(summary)
        
        # Verify backend was called
        mock_backend.chat_complete.assert_called_once()
        call_args = mock_backend.chat_complete.call_args
        
        # Check that messages were passed
        messages = call_args[0][0]
        assert isinstance(messages, list)
        assert len(messages) == 2
        
        # Check temperature and max_tokens
        kwargs = call_args[1]
        assert kwargs['temperature'] == 0.3
        assert kwargs['max_tokens'] == 1500
        
        # Check that code was returned
        assert code == "class MyAlgorithm:\n    pass"
    
    @patch('quantcli.backend_factory.make_backend')
    def test_openai_handler_refine_code_uses_backend(self, mock_make_backend):
        """Test that OpenAIHandler.refine_code uses backend.chat_complete."""
        mock_backend = Mock(spec=OllamaAdapter)
        mock_backend.chat_complete.return_value = "```python\nclass Fixed:\n    pass\n```"
        mock_make_backend.return_value = mock_backend
        
        handler = OpenAIHandler(backend=mock_backend)
        code = "class Broken:\n    syntax error"
        
        refined = handler.refine_code(code)
        
        # Verify backend was called
        mock_backend.chat_complete.assert_called_once()
        
        # Check that temperature is lower for refinement
        kwargs = mock_backend.chat_complete.call_args[1]
        assert kwargs['temperature'] == 0.2
        
        # Check that code was extracted from markdown
        assert refined == "class Fixed:\n    pass"
    
    @patch('quantcli.backend_factory.make_backend')
    def test_openai_handler_handles_backend_errors(self, mock_make_backend):
        """Test that OpenAIHandler handles backend errors gracefully."""
        mock_backend = Mock(spec=OllamaAdapter)
        mock_backend.chat_complete.side_effect = Exception("Backend error")
        mock_make_backend.return_value = mock_backend
        
        handler = OpenAIHandler(backend=mock_backend)
        extracted_data = {'trading_signal': [], 'risk_management': []}
        
        summary = handler.generate_summary(extracted_data)
        
        # Should return None on error
        assert summary is None
    
    def test_openai_handler_without_backend(self):
        """Test that OpenAIHandler can be created without backend (for compatibility)."""
        handler = OpenAIHandler(backend=None)
        
        assert handler.backend is None
        
        # Calling methods without backend should return None due to error handling
        extracted_data = {'trading_signal': [], 'risk_management': []}
        
        # Should return None instead of raising AttributeError due to error handling
        summary = handler.generate_summary(extracted_data)
        assert summary is None
