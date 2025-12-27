#!/usr/bin/env python
"""
Manual test script to demonstrate Ollama backend integration.

This script shows how to use the new backend adapter with quantcoder-cli.
Before running, ensure Ollama is running locally:
    ollama serve

And that you have a model pulled:
    ollama pull llama2
"""

import os
import sys

# Add the parent directory to the path so we can import quantcli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantcli.backend import OllamaAdapter
from quantcli.backend_factory import make_backend
from quantcli.processor import OpenAIHandler

def test_backend_creation():
    """Test creating a backend via the factory."""
    print("=" * 60)
    print("Test 1: Creating backend via factory")
    print("=" * 60)
    
    # Set environment variables
    os.environ['BACKEND'] = 'ollama'
    os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434'
    os.environ['OLLAMA_MODEL'] = 'llama2'
    
    try:
        backend = make_backend()
        print(f"✓ Backend created: {type(backend).__name__}")
        print(f"  Base URL: {backend.base_url}")
        print(f"  Model: {backend.model}")
        return backend
    except Exception as e:
        print(f"✗ Failed to create backend: {e}")
        return None

def test_simple_chat_completion(backend):
    """Test a simple chat completion."""
    print("\n" + "=" * 60)
    print("Test 2: Simple chat completion")
    print("=" * 60)
    
    if not backend:
        print("✗ Skipping - no backend available")
        return
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello World!' and nothing else."}
    ]
    
    try:
        print("Sending request to Ollama...")
        response = backend.chat_complete(messages, max_tokens=100, temperature=0.0)
        print(f"✓ Response received: {response}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        print("\nNote: Make sure Ollama is running (ollama serve) and has llama2 model downloaded (ollama pull llama2)")

def test_openai_handler_with_backend(backend):
    """Test OpenAIHandler with the backend."""
    print("\n" + "=" * 60)
    print("Test 3: OpenAIHandler integration")
    print("=" * 60)
    
    if not backend:
        print("✗ Skipping - no backend available")
        return
    
    handler = OpenAIHandler(backend=backend)
    
    # Test summary generation
    extracted_data = {
        'trading_signal': [
            'Buy when RSI is below 30',
            'Sell when RSI is above 70'
        ],
        'risk_management': [
            'Stop loss at 2% below entry',
            'Position size: 1% of portfolio per trade'
        ]
    }
    
    try:
        print("Generating summary...")
        summary = handler.generate_summary(extracted_data)
        if summary:
            print(f"✓ Summary generated ({len(summary)} chars):")
            print("-" * 60)
            print(summary[:200] + "..." if len(summary) > 200 else summary)
            print("-" * 60)
        else:
            print("✗ No summary generated")
    except Exception as e:
        print(f"✗ Failed: {e}")

def main():
    """Run all manual tests."""
    print("\n" + "=" * 60)
    print("Ollama Backend Integration - Manual Test")
    print("=" * 60)
    print()
    print("Prerequisites:")
    print("  1. Ollama must be running: ollama serve")
    print("  2. A model must be available: ollama pull llama2")
    print()
    
    # Test 1: Create backend
    backend = test_backend_creation()
    
    # Test 2: Simple chat completion
    test_simple_chat_completion(backend)
    
    # Test 3: OpenAIHandler integration
    test_openai_handler_with_backend(backend)
    
    print("\n" + "=" * 60)
    print("Manual tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
