# Contributing to QuantCoder CLI

Thank you for your interest in contributing to QuantCoder CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you are expected to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a branch for your changes
5. Make your changes and test them
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- [Ollama](https://ollama.ai) running locally
- A virtual environment tool (venv, conda, etc.)

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/quantcoder-cli.git
cd quantcoder-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Download required spacy model
python -m spacy download en_core_web_sm

# Pull required Ollama models
ollama pull qwen2.5-coder:14b
ollama pull mistral

# Verify installation
quantcoder --help
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=quantcoder --cov-report=term

# Run only integration tests
pytest tests/ -v -m integration

# Run only unit tests (exclude integration)
pytest tests/ -v -m "not integration"
```

### Code Quality Tools

```bash
# Format code with Black
black .

# Lint with Ruff
ruff check .

# Type checking with mypy
mypy quantcoder --ignore-missing-imports

# Security audit
pip-audit --require-hashes=false
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-indicator` - For new features
- `fix/search-timeout-issue` - For bug fixes
- `docs/update-readme` - For documentation
- `refactor/simplify-agent-logic` - For code refactoring

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Longer description if needed.

- Bullet points for multiple changes
- Keep lines under 72 characters
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(cli): add --timeout option to search command
fix(tools): handle network timeout in download tool
docs(readme): update installation instructions
test(integration): add CLI smoke tests
```

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass: `pytest tests/ -v`
   - Run linting: `black . && ruff check .`
   - Run type checking: `mypy quantcoder`
   - Update documentation if needed

2. **PR Description:**
   - Clearly describe what changes you made
   - Reference any related issues
   - Include screenshots for UI changes
   - List any breaking changes

3. **Review Process:**
   - PRs require at least one approval
   - Address all review comments
   - Keep PRs focused and reasonably sized

4. **After Merge:**
   - Delete your feature branch
   - Update your fork's main branch

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for formatting (line length: 100)
- Use type hints for function signatures
- Write docstrings for public functions and classes

### Code Organization

```
quantcoder/
├── __init__.py
├── cli.py           # CLI entry point
├── config.py        # Configuration management
├── chat.py          # Interactive chat
├── agents/          # Multi-agent system
├── tools/           # Pluggable tools
├── llm/             # LLM provider abstraction
├── evolver/         # Evolution engine
├── autonomous/      # Autonomous mode
├── library/         # Library builder
└── core/            # Core utilities
```

### Error Handling

- Use specific exception types (not bare `except:`)
- Provide helpful error messages
- Log errors with appropriate severity levels

### Security

- Never commit secrets or API keys
- Validate user inputs
- Use parameterized queries/requests
- Follow OWASP guidelines

## Testing

### Test Organization

- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_integration.py`
- Fixtures: `tests/conftest.py`

### Writing Tests

```python
import pytest
from quantcoder.tools import SearchArticlesTool

class TestSearchTool:
    """Tests for the search tool."""

    def test_search_returns_results(self, mock_config):
        """Test that search returns expected results."""
        tool = SearchArticlesTool(mock_config)
        result = tool.execute(query="momentum", max_results=5)
        assert result.success
        assert len(result.data) <= 5

    @pytest.mark.integration
    def test_search_integration(self):
        """Integration test with real API (marked for selective running)."""
        # This test hits real APIs
        pass
```

### Test Markers

- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.integration` - Integration tests
- Tests without markers run by default

## Documentation

### Code Documentation

- Add docstrings to all public functions/classes
- Use Google-style or NumPy-style docstrings
- Keep documentation up to date with code changes

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Document configuration options

### Architecture Documentation

- Update ARCHITECTURE.md for structural changes
- Document design decisions in ADRs if significant

## Questions?

- Open an issue for questions or discussions
- Tag maintainers for urgent issues
- Check existing issues before creating new ones

Thank you for contributing to QuantCoder CLI!
