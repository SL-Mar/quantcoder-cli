"""
Backend factory for creating LLM backend instances.

This module provides a factory function to instantiate the appropriate
backend adapter based on environment configuration.
"""

import os
import logging
from .backend import OllamaAdapter


logger = logging.getLogger(__name__)


def make_backend():
    """
    Create and return a backend adapter instance based on environment configuration.
    
    The backend is selected using the BACKEND environment variable:
    - 'ollama' (default): Returns an OllamaAdapter instance
    
    Returns:
        A backend adapter instance with a chat_complete() method
        
    Raises:
        ValueError: If BACKEND specifies an unsupported backend type
    """
    backend_type = os.environ.get('BACKEND', 'ollama').lower()
    
    logger.info(f"Creating backend adapter: {backend_type}")
    
    if backend_type == 'ollama':
        return OllamaAdapter()
    else:
        error_msg = (
            f"Unsupported backend type: '{backend_type}'. "
            f"Supported backends: 'ollama'. "
            f"Please set the BACKEND environment variable to a supported value."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
