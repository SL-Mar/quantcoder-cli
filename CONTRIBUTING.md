# Contributing to QuantCoder CLI

Thank you for your interest in contributing to QuantCoder CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)
- [Documentation](#documentation)

## Code of Conduct

This project follows a standard code of conduct. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Docker (optional, for container testing)

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/quantcoder-cli.git
cd quantcoder-cli
```

## Development Setup

### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate
```

### Install Dependencies

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Configure Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually (optional)
pre-commit run --all-files
```

### Set Up API Keys (for integration testing)

```bash
# Copy example environment file
cp .env.example ~/.quantcoder/.env
chmod 600 ~/.quantcoder/.env

# Edit and add your API keys
nano ~/.quantcoder/.env
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-tool` - New features
- `fix/circuit-breaker-timeout` - Bug fixes
- `docs/update-runbook` - Documentation
- `refactor/async-article-tools` - Refactoring
- `test/add-e2e-tests` - Test additions

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(tools): add async support to article search
fix(evolver): prevent race condition in parallel evaluation
docs(runbook): add circuit breaker troubleshooting
test(e2e): add workflow integration tests
```

## Testing

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=quantcoder --cov-report=html

# Run specific test file
pytest tests/test_tools.py -v

# Run specific test
pytest tests/test_tools.py::TestSearchTool::test_search_success -v
```

### Test Categories

```bash
# Run only unit tests (fast)
pytest -m "not (e2e or performance or integration)"

# Run E2E tests
pytest -m e2e

# Run performance tests
pytest -m performance

# Run integration tests
pytest -m integration
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures from `conftest.py`
- Mock external services (APIs, file system)

Example:
```python
import pytest
from unittest.mock import MagicMock, patch

class TestMyFeature:
    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.model.provider = "anthropic"
        return config

    def test_feature_success(self, mock_config):
        # Arrange
        tool = MyTool(mock_config)

        # Act
        result = tool.execute(param="value")

        # Assert
        assert result.success is True
```

## Submitting Changes

### Before Submitting

1. **Run the test suite**
   ```bash
   pytest
   ```

2. **Run linting**
   ```bash
   ruff check quantcoder/
   black --check quantcoder/
   ```

3. **Run type checking**
   ```bash
   mypy quantcoder/
   ```

4. **Run security scan**
   ```bash
   pip-audit
   ```

### Pull Request Process

1. **Create a PR** against the `main` branch
2. **Fill out the PR template** with:
   - Summary of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

3. **Wait for CI** to pass
4. **Address review feedback**
5. **Squash commits** if requested

### PR Title Format

```
type(scope): description (#issue)
```

Example: `feat(evolver): add parallel variant evaluation (#42)`

## Style Guidelines

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use Ruff for linting
- Use type hints where practical

### Code Organization

```
quantcoder/
├── __init__.py
├── cli.py              # CLI entry point
├── config.py           # Configuration management
├── tools/              # Tool implementations
│   ├── base.py         # Base classes
│   └── *.py            # Specific tools
├── agents/             # Multi-agent system
├── llm/                # LLM providers
└── ...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `SearchArticlesTool` |
| Functions | snake_case | `execute_search` |
| Constants | UPPER_SNAKE | `MAX_ARTICLE_ID` |
| Private | _prefix | `_search_crossref` |
| Async | async prefix | `async def _search_crossref_async` |

### Docstrings

Use Google-style docstrings:

```python
def execute(self, query: str, max_results: int = 5) -> ToolResult:
    """
    Search for articles using CrossRef API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        ToolResult with list of articles

    Raises:
        ValueError: If query is empty
    """
```

## Documentation

### When to Update Docs

- New features: Update README.md and relevant docs/
- API changes: Update docstrings
- Configuration changes: Update .env.example
- Bug fixes: Update CHANGELOG.md
- Operational changes: Update docs/RUNBOOK.md

### Documentation Files

| File | Purpose |
|------|---------|
| README.md | Quick start and overview |
| CHANGELOG.md | Version history |
| CONTRIBUTING.md | This file |
| docs/ARCHITECTURE.md | System architecture |
| docs/RUNBOOK.md | Operational procedures |
| .env.example | Configuration template |

## Questions?

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact smr.laignel@gmail.com for sensitive matters

Thank you for contributing!
