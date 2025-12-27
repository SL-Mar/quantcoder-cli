"""
Tests for backend factory.
"""

import os
import pytest
from quantcli.backend_factory import make_backend
from quantcli.backend import OllamaAdapter


class TestBackendFactory:
    """Test suite for backend factory function."""
    
    def test_make_backend_default_ollama(self):
        """Test that default backend is Ollama."""
        # Clear BACKEND env var
        env_backup = os.environ.get('BACKEND')
        if 'BACKEND' in os.environ:
            del os.environ['BACKEND']
        
        try:
            backend = make_backend()
            assert isinstance(backend, OllamaAdapter)
        finally:
            # Restore environment
            if env_backup is not None:
                os.environ['BACKEND'] = env_backup
    
    def test_make_backend_ollama_explicit(self):
        """Test explicitly requesting Ollama backend."""
        os.environ['BACKEND'] = 'ollama'
        
        try:
            backend = make_backend()
            assert isinstance(backend, OllamaAdapter)
        finally:
            if 'BACKEND' in os.environ:
                del os.environ['BACKEND']
    
    def test_make_backend_ollama_case_insensitive(self):
        """Test that BACKEND env var is case-insensitive."""
        os.environ['BACKEND'] = 'OLLAMA'
        
        try:
            backend = make_backend()
            assert isinstance(backend, OllamaAdapter)
        finally:
            if 'BACKEND' in os.environ:
                del os.environ['BACKEND']
    
    def test_make_backend_unsupported(self):
        """Test that unsupported backend raises ValueError."""
        os.environ['BACKEND'] = 'unsupported_backend'
        
        try:
            with pytest.raises(ValueError) as exc_info:
                make_backend()
            
            assert "Unsupported backend type" in str(exc_info.value)
            assert "unsupported_backend" in str(exc_info.value)
        finally:
            if 'BACKEND' in os.environ:
                del os.environ['BACKEND']
