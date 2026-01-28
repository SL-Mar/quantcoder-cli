# QuantCoder 2.0.0

[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/SL-Mar/quantcoder-cli)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-available-blue)](https://github.com/SL-Mar/quantcoder-cli)

> **AI-powered CLI for generating QuantConnect trading algorithms from research articles**

Features: Multi-agent system, AlphaEvolve-inspired evolution, autonomous learning, MCP integration.

---

QuantCoder is a command-line tool that allows users to generate QuantConnect trading algorithms from research articles using natural language processing and large language models (LLMs). It was initiated in November 2023 and based on a cognitive architecture inspired by the article ["Dual Agent Chatbots and Expert Systems Design"](https://towardsdev.com/dual-agent-chatbots-and-expert-systems-design-25e2cba434e9)

The initial version successfully coded a blended momentum and mean-reversion strategy as described in ["Outperforming the Market (1000% in 10 years)"](https://medium.com/coinmonks/how-to-outperform-the-market-fe151b944c77?sk=7066045abe12d5cf88c7edc80ec2679c), which received over 10,000 impressions on LinkedIn.

## 🌟 Version 2.0 - Complete Refactoring

**Refactored in December 2025** - Inspired by [Mistral's Vibe CLI](https://github.com/mistralai/mistral-vibe) architecture.

### New Features:
- 🤖 **Interactive Chat Interface** with conversational AI
- 🛠️ **Tool-Based Architecture** for modularity and extensibility
- ⚙️ **Configuration System** with TOML support
- 🎨 **Modern Terminal UI** with Rich library
- 📝 **Programmable Mode** via `--prompt` flag
- 💾 **Persistent Context** and conversation history

📖 **[Architecture](docs/AGENTIC_WORKFLOW.md)** | **[Autonomous Mode](docs/AUTONOMOUS_MODE.md)** | **[Changelog](CHANGELOG.md)**

---

## 🚀 Installation (v2.0)

> ✅ Requires **Python 3.10 or later**

### Quick Start

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

### Docker Installation

```bash
# Build the Docker image
docker build -t quantcoder-cli:2.0.0 .

# Run with environment variables
docker run -it --rm \
  -e OPENAI_API_KEY=your-key \
  -e ANTHROPIC_API_KEY=your-key \
  -v quantcoder-config:/home/quantcoder/.quantcoder \
  quantcoder-cli:2.0.0

# Or use docker-compose
docker-compose run quantcoder
```

### First Run

```bash
# Launch interactive mode
quantcoder

# Or use the short alias
qc
```

On first run, you'll be prompted for your OpenAI API key.

---

## 💡 Usage (v2.0)

QuantCoder offers multiple modes of operation to suit different workflows.

### Interactive Mode

Launch the interactive chat interface for a conversational experience:

```bash
# Start interactive mode
quantcoder

# Or use the short alias
qc
```

In interactive mode, you can use natural language or direct commands:

```bash
quantcoder> search "momentum trading strategies"
quantcoder> download 1
quantcoder> summarize 1
quantcoder> generate 1
```

### Programmatic Mode

Run commands non-interactively using the `--prompt` flag:

```bash
quantcoder --prompt "Find articles about mean reversion"
```

---

## 📖 CLI Commands Reference

### Core Commands

#### `search` - Search for Academic Articles

Search for research articles on CrossRef using keywords.

```bash
quantcoder search "algorithmic trading" --num 5
```

**Arguments:**
- `query` - Search query string (required)

**Options:**
- `--num` - Number of results to return (default: 5)

**Example:**
```bash
quantcoder search "momentum trading strategies" --num 10
```

---

#### `download` - Download Article PDF

Download a research article PDF by its ID from the search results.

```bash
quantcoder download 1
```

**Arguments:**
- `article_id` - ID of the article from search results (required)

**Example:**
```bash
quantcoder download 3
```

---

#### `summarize` - Summarize Article

Analyze and summarize a downloaded article using AI.

```bash
quantcoder summarize 1
```

**Arguments:**
- `article_id` - ID of the downloaded article (required)

**Example:**
```bash
quantcoder summarize 1
```

---

#### `generate` - Generate QuantConnect Code

Generate trading algorithm code from a research article.

```bash
quantcoder generate 1
quantcoder generate 1 --open-in-editor
quantcoder generate 1 --open-in-editor --editor code
```

**Arguments:**
- `article_id` - ID of the article to generate code from (required)

**Options:**
- `--max-attempts` - Maximum refinement attempts (default: 6)
- `--open-in-editor` - Open generated code in editor (default: false)
- `--editor` - Editor to use (e.g., zed, code, vim)

**Example:**
```bash
quantcoder generate 2 --open-in-editor --editor zed
```

---

#### `validate` - Validate Algorithm Code

Validate algorithm code locally and optionally on QuantConnect.

```bash
quantcoder validate generated_code/algorithm_1.py
quantcoder validate my_algo.py --local-only
```

**Arguments:**
- `file_path` - Path to the algorithm file (required)

**Options:**
- `--local-only` - Only run local syntax check, skip QuantConnect validation

**Example:**
```bash
quantcoder validate generated_code/algorithm_1.py
```

---

#### `backtest` - Run Backtest on QuantConnect

Execute a backtest on QuantConnect with the specified algorithm.

**Requirements:** Set `QUANTCONNECT_API_KEY` and `QUANTCONNECT_USER_ID` in `~/.quantcoder/.env`

```bash
quantcoder backtest generated_code/algorithm_1.py
quantcoder backtest my_algo.py --start 2022-01-01 --end 2024-01-01
```

**Arguments:**
- `file_path` - Path to the algorithm file (required)

**Options:**
- `--start` - Backtest start date in YYYY-MM-DD format (default: 2020-01-01)
- `--end` - Backtest end date in YYYY-MM-DD format (default: 2024-01-01)
- `--name` - Name for the backtest

**Example:**
```bash
quantcoder backtest my_algo.py --start 2023-01-01 --end 2024-01-01 --name "My Strategy v1"
```

---

### Autonomous Mode Commands

Autonomous mode runs continuously, learning from errors and self-improving strategies over time.

#### `auto start` - Start Autonomous Strategy Generation

```bash
quantcoder auto start --query "momentum trading" --max-iterations 50
```

**Options:**
- `--query` - Strategy query (e.g., "momentum trading") (required)
- `--max-iterations` - Maximum iterations to run (default: 50)
- `--min-sharpe` - Minimum Sharpe ratio threshold (default: 0.5)
- `--output` - Output directory for strategies
- `--demo` - Run in demo mode (no real API calls)

**Example:**
```bash
quantcoder auto start --query "mean reversion" --max-iterations 100 --min-sharpe 1.0
```

---

#### `auto status` - Show Autonomous Mode Status

Display statistics and learning progress from autonomous mode.

```bash
quantcoder auto status
```

Shows:
- Total strategies generated
- Success rate
- Average Sharpe ratio
- Common errors and fix rates

---

#### `auto report` - Generate Learning Report

Generate a comprehensive report from autonomous mode runs.

```bash
quantcoder auto report --format text
quantcoder auto report --format json
```

**Options:**
- `--format` - Report format: text or json (default: text)

---

### Library Builder Commands

Library builder mode systematically generates strategies across all major categories.

#### `library build` - Build Strategy Library

Build a comprehensive library of trading strategies.

```bash
quantcoder library build --comprehensive --max-hours 24
quantcoder library build --categories momentum,mean_reversion
```

**Options:**
- `--comprehensive` - Build all categories
- `--max-hours` - Maximum build time in hours (default: 24)
- `--output` - Output directory for library
- `--min-sharpe` - Minimum Sharpe ratio threshold (default: 0.5)
- `--categories` - Comma-separated list of categories to build
- `--demo` - Run in demo mode (no real API calls)

**Example:**
```bash
quantcoder library build --categories momentum,arbitrage --max-hours 12
```

---

#### `library status` - Show Library Build Progress

Display the current progress of library building.

```bash
quantcoder library status
```

---

#### `library resume` - Resume Library Build

Resume an interrupted library build from checkpoint.

```bash
quantcoder library resume
```

---

#### `library export` - Export Completed Library

Export the completed strategy library.

```bash
quantcoder library export --format zip --output library.zip
quantcoder library export --format json --output library.json
```

**Options:**
- `--format` - Export format: zip or json (default: zip)
- `--output` - Output file path

---

### Evolution Mode Commands (AlphaEvolve-Inspired)

Evolution mode uses LLM-generated variations to optimize trading algorithms through structural changes.

#### `evolve start` - Start Strategy Evolution

Evolve a trading algorithm through multiple generations of variations.

```bash
quantcoder evolve start 1
quantcoder evolve start 1 --gens 5
quantcoder evolve start --code algo.py
quantcoder evolve start --resume abc123
```

**Arguments:**
- `article_id` - Article number to evolve (optional if using --code or --resume)

**Options:**
- `--code` - Path to algorithm file to evolve
- `--resume` - Resume a previous evolution by ID
- `--gens` - Maximum generations to run (default: 10)
- `--variants` - Variants per generation (default: 5)
- `--elite` - Elite pool size (default: 3)
- `--patience` - Stop after N generations without improvement (default: 3)
- `--qc-user` - QuantConnect user ID (or set QC_USER_ID env var)
- `--qc-token` - QuantConnect API token (or set QC_API_TOKEN env var)
- `--qc-project` - QuantConnect project ID (or set QC_PROJECT_ID env var)

**Example:**
```bash
quantcoder evolve start 1 --gens 20 --variants 10 --qc-user 123456 --qc-token abc123 --qc-project 789
```

**Note:** Evolution explores structural variations like:
- Indicator changes (SMA → EMA, adding RSI, etc.)
- Risk management modifications
- Entry/exit logic changes
- Universe selection tweaks

---

#### `evolve list` - List Saved Evolutions

Show all saved evolution runs with their status and performance.

```bash
quantcoder evolve list
```

---

#### `evolve show` - Show Evolution Details

Display detailed information about a specific evolution.

```bash
quantcoder evolve show abc123
```

**Arguments:**
- `evolution_id` - The evolution ID to show (required)

---

#### `evolve export` - Export Best Algorithm

Export the best algorithm from an evolution run.

```bash
quantcoder evolve export abc123
quantcoder evolve export abc123 --output my_best_algo.py
```

**Arguments:**
- `evolution_id` - The evolution ID to export from (required)

**Options:**
- `--output` - Output file path

---

### Utility Commands

#### `config-show` - Show Current Configuration

Display the current QuantCoder configuration.

```bash
quantcoder config-show
```

Shows:
- Model configuration (provider, model, temperature, max tokens)
- UI configuration (theme, auto-approve, token usage display)
- Tools configuration (directories, enabled tools)
- Paths (home directory, config file)

---

#### `version` - Show Version Information

Display the current version of QuantCoder.

```bash
quantcoder version
```

---

### Global Options

These options can be used with any command:

- `--verbose` or `-v` - Enable verbose logging
- `--config` - Path to custom config file
- `--prompt` or `-p` - Run in non-interactive mode with a prompt

**Example:**
```bash
quantcoder --verbose search "algorithmic trading"
quantcoder --config my_config.toml generate 1
```

---

## 📁 Articles and Strategies

The folder 'Strategies and publications' contains articles and trading strategies generated using this CLI tool. These strategies may have been manually refined or enhanced using LLM-based methods. Use them at your own discretion — conduct thorough research and validate before live use.

---

## 📜 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.


