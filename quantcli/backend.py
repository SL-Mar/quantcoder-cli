"""
Backend adapters for LLM services.

This module provides adapters for different LLM backends to allow flexible
integration with various AI services like Ollama, OpenAI, etc.
"""

import os
import logging
import requests
from typing import List, Dict, Optional


class OllamaAdapter:
    """Adapter for Ollama-backed LLM services."""
    
    def __init__(self):
        """Initialize the Ollama adapter with configuration from environment variables."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.environ.get('OLLAMA_MODEL', 'llama2')
        self.logger.info(f"Initialized OllamaAdapter with base_url={self.base_url}, model={self.model}")
    
    def chat_complete(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 1500, 
        temperature: float = 0.0
    ) -> str:
        """
        Send a chat completion request to Ollama and return the response text.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            max_tokens: Maximum number of tokens to generate (passed as num_predict)
            temperature: Sampling temperature for generation
            
        Returns:
            The generated text response from the model
            
        Raises:
            requests.RequestException: If the HTTP request fails
            ValueError: If the response format is unexpected
        """
        self.logger.info(f"Sending chat completion request to Ollama (model={self.model})")
        
        # Convert messages to a single prompt for Ollama's generate endpoint
        prompt = self._format_messages_as_prompt(messages)
        
        # Prepare the request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        # Make the API request
        url = f"{self.base_url}/api/generate"
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Try to extract text from various possible response formats
            if 'response' in result:
                text = result['response']
            elif 'text' in result:
                text = result['text']
            elif 'output' in result:
                text = result['output']
            elif 'choices' in result and len(result['choices']) > 0:
                # OpenAI-compatible format
                choice = result['choices'][0]
                if 'message' in choice:
                    text = choice['message'].get('content', '')
                elif 'text' in choice:
                    text = choice['text']
                else:
                    raise ValueError(f"Unexpected choice format: {choice}")
            else:
                raise ValueError(f"Unexpected response format from Ollama: {result}")
            
            self.logger.info(f"Successfully received response from Ollama ({len(text)} chars)")
            return text.strip()
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout connecting to Ollama at {url}: {e}"
            self.logger.error(error_msg)
            raise requests.RequestException(error_msg) from e
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to Ollama at {url}. Is Ollama running? Error: {e}"
            self.logger.error(error_msg)
            raise requests.RequestException(error_msg) from e
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error from Ollama API: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg)
            raise requests.RequestException(error_msg) from e
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error communicating with Ollama: {e}"
            self.logger.error(error_msg)
            raise
            
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Failed to parse response from Ollama: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def _format_messages_as_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert OpenAI-style messages into a single prompt string for Ollama.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
            else:
                prompt_parts.append(content)
        
        # Join with double newlines for clarity
        prompt = "\n\n".join(prompt_parts)
        
        # Add a final prompt for the assistant to respond
        prompt += "\n\nAssistant:"
        
        return prompt
