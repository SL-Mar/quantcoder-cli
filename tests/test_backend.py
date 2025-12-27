"""
Tests for backend adapters.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from quantcli.backend import OllamaAdapter


class TestOllamaAdapter:
    """Test suite for OllamaAdapter class."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        # Clear environment variables
        env_backup = {}
        for key in ['OLLAMA_BASE_URL', 'OLLAMA_MODEL']:
            env_backup[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
        
        try:
            adapter = OllamaAdapter()
            assert adapter.base_url == 'http://localhost:11434'
            assert adapter.model == 'llama2'
        finally:
            # Restore environment
            for key, value in env_backup.items():
                if value is not None:
                    os.environ[key] = value
    
    def test_init_custom_values(self):
        """Test initialization with custom environment values."""
        os.environ['OLLAMA_BASE_URL'] = 'http://custom:8080'
        os.environ['OLLAMA_MODEL'] = 'mistral'
        
        try:
            adapter = OllamaAdapter()
            assert adapter.base_url == 'http://custom:8080'
            assert adapter.model == 'mistral'
        finally:
            # Clean up
            if 'OLLAMA_BASE_URL' in os.environ:
                del os.environ['OLLAMA_BASE_URL']
            if 'OLLAMA_MODEL' in os.environ:
                del os.environ['OLLAMA_MODEL']
    
    @patch('requests.post')
    def test_chat_complete_success_response_field(self, mock_post):
        """Test successful chat completion with 'response' field."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'This is a test response'}
        mock_post.return_value = mock_response
        
        adapter = OllamaAdapter()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        
        result = adapter.chat_complete(messages, max_tokens=100, temperature=0.7)
        
        assert result == 'This is a test response'
        mock_post.assert_called_once()
        
        # Check that the call was made with correct parameters
        call_args = mock_post.call_args
        assert call_args[0][0] == 'http://localhost:11434/api/generate'
        assert 'json' in call_args[1]
        payload = call_args[1]['json']
        assert payload['model'] == 'llama2'
        assert payload['stream'] is False
        assert 'prompt' in payload
        assert 'options' in payload
        assert payload['options']['temperature'] == 0.7
        assert payload['options']['num_predict'] == 100
    
    @patch('requests.post')
    def test_chat_complete_success_text_field(self, mock_post):
        """Test successful chat completion with 'text' field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'text': 'Response text'}
        mock_post.return_value = mock_response
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        result = adapter.chat_complete(messages)
        
        assert result == 'Response text'
    
    @patch('requests.post')
    def test_chat_complete_success_choices_format(self, mock_post):
        """Test successful chat completion with OpenAI-compatible format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {'message': {'content': 'OpenAI format response'}}
            ]
        }
        mock_post.return_value = mock_response
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        result = adapter.chat_complete(messages)
        
        assert result == 'OpenAI format response'
    
    @patch('requests.post')
    def test_chat_complete_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(requests.RequestException) as exc_info:
            adapter.chat_complete(messages)
        
        assert "Failed to connect to Ollama" in str(exc_info.value)
    
    @patch('requests.post')
    def test_chat_complete_timeout(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(requests.RequestException) as exc_info:
            adapter.chat_complete(messages)
        
        assert "Timeout connecting to Ollama" in str(exc_info.value)
    
    @patch('requests.post')
    def test_chat_complete_http_error(self, mock_post):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(requests.RequestException) as exc_info:
            adapter.chat_complete(messages)
        
        assert "HTTP error from Ollama API" in str(exc_info.value)
    
    @patch('requests.post')
    def test_chat_complete_unexpected_format(self, mock_post):
        """Test handling of unexpected response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'unexpected': 'format'}
        mock_post.return_value = mock_response
        
        adapter = OllamaAdapter()
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(ValueError) as exc_info:
            adapter.chat_complete(messages)
        
        assert "Unexpected response format" in str(exc_info.value)
    
    def test_format_messages_as_prompt(self):
        """Test message formatting for Ollama."""
        adapter = OllamaAdapter()
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
        
        prompt = adapter._format_messages_as_prompt(messages)
        
        assert "System: You are helpful" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt
        assert "User: How are you?" in prompt
        assert prompt.endswith("\n\nAssistant:")
