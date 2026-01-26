# QuantCoder v2.0

> **AI-powered CLI for generating QuantConnect trading algorithms from research articles**

QuantCoder v2.0 is a complete refactoring inspired by [Mistral's Vibe CLI](https://github.com/mistralai/mistral-vibe), featuring a modern architecture with conversational AI, tool-based workflows, and an enhanced developer experience.

---

## 🌟 What's New in v2.0

### Inspired by Mistral Vibe CLI

This version draws inspiration from Mistral's excellent Vibe CLI architecture:

- **🤖 Interactive Chat Interface**: Conversational AI that understands natural language
- **🛠️ Tool-Based Architecture**: Modular, extensible tool system
- **⚙️ Configuration System**: Customizable via TOML config files
- **🎨 Modern UI**: Beautiful terminal output with Rich library
- **📝 Programmable Mode**: Use `--prompt` for automation
- **💾 Persistent Context**: Conversation history and smart completions

### Core Improvements

- Modern Python packaging with `pyproject.toml`
- Updated OpenAI SDK (v1.0+)
- Rich terminal UI with syntax highlighting
- Prompt-toolkit for advanced CLI features
- Configuration management system
- Tool approval workflows
- Better error handling and logging

---

## 🚀 Installation

### Prerequisites

- **Python 3.10 or later**
- OpenAI API key

### Install from Source

```bash
# Clone the repository
git clone https://github.com/SL-Mar/quantcoder-cli.git
cd quantcoder-cli

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Download SpaCy model
python -m spacy download en_core_web_sm
```

### Quick Install (pip)

```bash
pip install -e .
python -m spacy download en_core_web_sm
```

---

## 🎯 Quick Start

### First Run

On first run, QuantCoder will:
1. Create configuration directory at `~/.quantcoder/`
2. Generate default `config.toml`
3. Prompt for your OpenAI API key (saved to `~/.quantcoder/.env`)

### Launch Interactive Mode

```bash
quantcoder
```

Or use the short alias:

```bash
qc
```

### Programmatic Mode

```bash
quantcoder --prompt "Search for momentum trading strategies"
```

---

## 💡 Usage

### Interactive Mode

QuantCoder provides a conversational interface:

```bash
quantcoder> search momentum trading
quantcoder> download 1
quantcoder> summarize 1
quantcoder> generate 1
```

You can also use natural language:

```bash
quantcoder> Find articles about algorithmic trading
quantcoder> How do I generate code from an article?
quantcoder> Explain mean reversion strategies
```

### Direct Commands

```bash
# Search for articles
quantcoder search "algorithmic trading" --num 5

# Download article by ID
quantcoder download 1

# Summarize trading strategy
quantcoder summarize 1

# Generate QuantConnect code
quantcoder generate 1

# Show configuration
quantcoder config-show

# Show version
quantcoder version
```

### Workflow Example

```bash
# 1. Search for articles
quantcoder> search "momentum and mean reversion strategies"

# 2. Download the most relevant article
quantcoder> download 1

# 3. Extract and summarize the trading strategy
quantcoder> summarize 1

# 4. Generate QuantConnect algorithm code
quantcoder> generate 1
```

---

## ⚙️ Configuration

### Config File Location

`~/.quantcoder/config.toml`

### Example Configuration

```toml
[model]
provider = "openai"
model = "gpt-4o-2024-11-20"
temperature = 0.5
max_tokens = 2000

[ui]
theme = "monokai"
auto_approve = false
show_token_usage = true

[tools]
enabled_tools = ["*"]
disabled_tools = []
downloads_dir = "downloads"
generated_code_dir = "generated_code"
```

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `QUANTCODER_HOME`: Override default config directory (default: `~/.quantcoder`)

### API Key Setup

Three ways to set your API key:

1. **Interactive prompt** (first-time setup)
2. **Environment variable**: `export OPENAI_API_KEY=your_key`
3. **`.env` file**: Create `~/.quantcoder/.env` with `OPENAI_API_KEY=your_key`

---

## 🏗️ Architecture

### Directory Structure

```
quantcoder/
├── __init__.py          # Package initialization
├── cli.py               # Main CLI interface
├── config.py            # Configuration management
├── chat.py              # Interactive & programmatic chat
├── core/
│   ├── __init__.py
│   ├── llm.py           # LLM handler (OpenAI)
│   └── processor.py     # Article processing pipeline
├── tools/
│   ├── __init__.py
│   ├── base.py          # Base tool classes
│   ├── article_tools.py # Search, download, summarize
│   ├── code_tools.py    # Generate, validate code
│   └── file_tools.py    # Read, write files
└── agents/
    └── __init__.py      # Future: custom agents
```

### Tool System

Tools are modular, composable components:

- **ArticleTools**: Search, download, summarize articles
- **CodeTools**: Generate and validate QuantConnect code
- **FileTools**: Read and write files

Each tool:
- Has a clear interface (`execute(**kwargs) -> ToolResult`)
- Can be enabled/disabled via configuration
- Supports approval workflows
- Provides rich error handling

### LLM Integration

- Supports OpenAI API (v1.0+)
- Configurable models, temperature, max tokens
- Context-aware conversations
- Automatic code refinement with validation

---

## 🎨 Features

### Interactive Chat

- **Prompt Toolkit**: Advanced line editing, history, auto-suggest
- **Natural Language**: Ask questions in plain English
- **Context Awareness**: Maintains conversation history
- **Smart Completions**: Auto-complete for commands

### Rich Terminal UI

- **Syntax Highlighting**: Beautiful code display with Pygments
- **Markdown Rendering**: Formatted summaries and help
- **Progress Indicators**: Status messages for long operations
- **Color-Coded Output**: Errors, success, info messages

### Tool Approval

- **Auto-Approve Mode**: For trusted operations
- **Manual Approval**: Review before execution (coming soon)
- **Safety Controls**: Configurable tool permissions

---

## 📚 Comparison with Legacy Version

| Feature | Legacy (v0.3) | v2.0 |
|---------|---------------|------|
| Python Version | 3.8+ | 3.10+ |
| OpenAI SDK | 0.28 | 1.0+ |
| CLI Framework | Click | Click + Rich + Prompt Toolkit |
| Architecture | Monolithic | Tool-based, modular |
| Configuration | Hardcoded | TOML config file |
| UI | Basic text | Rich terminal UI |
| Interactive Mode | Tkinter GUI | Conversational CLI |
| Programmable | No | Yes (`--prompt` flag) |
| Extensibility | Limited | Plugin-ready |

---

## 🛠️ Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black quantcoder/

# Lint code
ruff check quantcoder/

# Type checking
mypy quantcoder/

# Run tests
pytest
```

### Project Structure

The project follows modern Python best practices:

- **pyproject.toml**: Single source of truth for dependencies
- **Type hints**: Improved code quality and IDE support
- **Logging**: Structured logging with Rich
- **Modularity**: Clear separation of concerns

---

## 🤝 Contributing

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Mistral AI** - For the excellent [Vibe CLI](https://github.com/mistralai/mistral-vibe) architecture that inspired this refactoring
- **OpenAI** - For GPT models powering the code generation
- **QuantConnect** - For the algorithmic trading platform
- Original QuantCoder concept from November 2023

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/SL-Mar/quantcoder-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SL-Mar/quantcoder-cli/discussions)
- **Email**: smr.laignel@gmail.com

---

## 🗺️ Roadmap

- [ ] Custom agent system for specialized workflows
- [ ] MCP server integration for external tools
- [ ] Web interface option
- [ ] Backtesting integration with QuantConnect
- [ ] Strategy optimization tools
- [ ] Multi-provider LLM support (Anthropic, Mistral, etc.)
- [ ] Plugin system for custom tools

---

**Note**: This is v2.0 with breaking changes from the legacy version. For the original version, see the `quantcoder-legacy` branch.

---

## Sources

This refactoring was inspired by:
- [GitHub - mistralai/mistral-vibe](https://github.com/mistralai/mistral-vibe)
- [Introducing: Devstral 2 and Mistral Vibe CLI | Mistral AI](https://mistral.ai/news/devstral-2-vibe-cli)
