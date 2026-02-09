# QuantCoder 2.0.0

[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/SL-Mar/quantcoder-cli)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> **Local-first CLI for generating QuantConnect trading algorithms from research papers — powered by Ollama**

QuantCoder transforms academic quant research into compilable QuantConnect LEAN algorithms using local LLMs. No cloud API keys required.

**Models:**
- **qwen2.5-coder:14b** — code generation, refinement, error fixing
- **mistral** — reasoning, summarization, chat

---

## Installation

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) running locally

```bash
# Pull the required models
ollama pull qwen2.5-coder:14b
ollama pull mistral
```

### Setup

```bash
git clone https://github.com/SL-Mar/quantcoder-cli.git
cd quantcoder-cli

python -m venv .venv
source .venv/bin/activate

pip install -e .
python -m spacy download en_core_web_sm
```

### Verify

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Launch QuantCoder
quantcoder
```

---

## Usage

### Interactive Mode

```bash
quantcoder        # or: qc
```

### CLI Commands

```bash
# Search for papers
quantcoder search "momentum trading" --num 5

# Download and summarize
quantcoder download 1
quantcoder summarize 1

# Generate QuantConnect algorithm
quantcoder generate 1
quantcoder generate 1 --open-in-editor

# Validate and backtest (requires QC credentials)
quantcoder validate generated_code/algorithm_1.py
quantcoder backtest generated_code/algorithm_1.py --start 2022-01-01 --end 2024-01-01
```

### Programmatic Mode

```bash
quantcoder --prompt "Find articles about mean reversion"
```

### Autonomous Mode

```bash
quantcoder auto start --query "momentum trading" --max-iterations 50
quantcoder auto status
```

### Evolution Mode (AlphaEvolve-inspired)

```bash
quantcoder evolve start 1 --gens 3 --variants 5
quantcoder evolve start 1 --gens 3 --push-to-qc   # Push best to QC
quantcoder evolve list
quantcoder evolve export abc123
```

### Backtest with Detailed Metrics

```bash
# Shows Sharpe, Total Return, CAGR, Max Drawdown, Win Rate, Total Trades
quantcoder backtest generated_code/algorithm_1.py --start 2022-01-01 --end 2024-01-01
```

### Library Builder

```bash
quantcoder library build --comprehensive --max-hours 24
quantcoder library status
```

---

## Configuration

Configuration is stored in `~/.quantcoder/config.toml`:

```toml
[model]
provider = "ollama"
model = "qwen2.5-coder:14b"
code_model = "qwen2.5-coder:14b"
reasoning_model = "mistral"
ollama_base_url = "http://localhost:11434"
ollama_timeout = 600
temperature = 0.5
max_tokens = 3000

[ui]
theme = "monokai"
editor = "zed"
```

### QuantConnect Integration

For backtesting and deployment, set credentials in `~/.quantcoder/.env`:

```
QUANTCONNECT_API_KEY=your_key
QUANTCONNECT_USER_ID=your_id
```

### Remote Ollama

To use a remote Ollama instance:

```toml
[model]
ollama_base_url = "http://your-server:11434"
```

---

## Architecture

```
quantcoder/
├── cli.py           # CLI entry point
├── config.py        # Configuration management
├── chat.py          # Interactive chat
├── llm/             # Ollama provider layer
├── core/            # LLM handler, processor, NLP
├── agents/          # Multi-agent system (Coordinator, Alpha, Risk, Universe)
├── evolver/         # AlphaEvolve-inspired evolution engine
├── autonomous/      # Self-improving pipeline
├── library/         # Batch strategy library builder
├── tools/           # Pluggable tool system
└── mcp/             # QuantConnect MCP integration
```

---

## Background

QuantCoder was initiated in November 2023 based on ["Dual Agent Chatbots and Expert Systems Design"](https://towardsdev.com/dual-agent-chatbots-and-expert-systems-design-25e2cba434e9). The initial version coded a blended momentum/mean-reversion strategy from ["Outperforming the Market (1000% in 10 years)"](https://medium.com/coinmonks/how-to-outperform-the-market-fe151b944c77?sk=7066045abe12d5cf88c7edc80ec2679c), which received over 10,000 impressions on LinkedIn.

v2.0.0 is a complete rewrite — local-only inference, multi-agent architecture, evolution engine, and autonomous learning.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
