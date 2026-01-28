# QuantCoder CLI - Complete Guide

> AI-powered CLI for transforming research papers into QuantConnect trading algorithms

---

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Two Workflows](#two-workflows)
4. [CLI Commands Reference](#cli-commands-reference)
5. [Configuration](#configuration)
6. [Logging & Monitoring](#logging--monitoring)
7. [Deep Search with Tavily](#deep-search-with-tavily)
8. [Strategy Evolution](#strategy-evolution)
9. [Notion Integration](#notion-integration)
10. [Environment Variables](#environment-variables)

---

## Overview

QuantCoder is a conversational CLI tool that automates the research-to-algorithm pipeline:

```
Research Paper → Summary → QuantConnect Code → Backtest → Evolution → Publish
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Paper Discovery** | Search academic papers via CrossRef or semantic deep search (Tavily) |
| **Multi-Article Workflow** | Combine insights from multiple papers into consolidated strategies |
| **Code Generation** | Generate QuantConnect-compatible Python algorithms |
| **Auto-Refinement** | Automatically fix compilation errors with LLM assistance |
| **Backtesting** | Run backtests on QuantConnect cloud |
| **Evolution** | AlphaEvolve-inspired strategy optimization |
| **Scheduling** | Automated daily/weekly pipeline runs |
| **Notion Publishing** | Publish successful strategies as articles |
| **Comprehensive Logging** | Structured logs with rotation and alerting |

---

## Installation & Setup

### 1. Clone and Install

```bash
git clone https://github.com/SL-Mar/quantcoder-cli.git
cd quantcoder-cli
pip install -e .
```

### 2. Configure API Keys

```bash
# Interactive setup
quantcoder schedule config --show

# Set individual keys
quantcoder schedule config --notion-key secret_xxx --notion-db abc123
quantcoder schedule config --tavily-key tvly-xxx
```

Or manually create `~/.quantcoder/.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-xxx
# or
OPENAI_API_KEY=sk-xxx

# QuantConnect (for backtesting)
QUANTCONNECT_API_KEY=xxx
QUANTCONNECT_USER_ID=xxx

# Optional integrations
NOTION_API_KEY=secret_xxx
NOTION_DATABASE_ID=xxx
TAVILY_API_KEY=tvly-xxx

# Alerting (optional)
QUANTCODER_WEBHOOK_URL=https://hooks.slack.com/...
```

### 3. Verify Setup

```bash
quantcoder --help
quantcoder schedule config --show
```

---

## Two Workflows

### Workflow 1: Spot Generation (Manual/Interactive)

For ad-hoc strategy generation with full control over each step.

```bash
# Step 1: Search for papers
quantcoder search "momentum trading strategies" --num 5

# Or use deep semantic search
quantcoder search "mean reversion with machine learning" --deep

# Step 2: Download a paper
quantcoder download 1 2 3

# Step 3: Summarize and extract strategy
quantcoder summarize 1

# Step 4: Generate code (with optional backtest and evolution)
quantcoder generate 1 --backtest --evolve --gens 5
```

#### Spot Generation Options

```bash
quantcoder generate <SUMMARY_ID> [OPTIONS]

Options:
  --max-attempts INT     Maximum refinement attempts (default: 6)
  --open-in-editor       Open generated code in editor
  --editor TEXT          Editor to use (zed, code, vim)
  --backtest             Run backtest on QuantConnect
  --min-sharpe FLOAT     Min Sharpe to keep algo (default: 0.5)
  --start-date TEXT      Backtest start date (default: 2020-01-01)
  --end-date TEXT        Backtest end date (default: 2024-01-01)
  --evolve               Evolve strategy after backtest passes
  --gens INT             Evolution generations (default: 5)
  --variants INT         Variants per generation (default: 3)
```

### Workflow 2: Batch Mode (Automated/Scheduled)

For hands-off automated strategy discovery and generation.

#### One-Time Run

```bash
# Run the full pipeline once
quantcoder schedule run

# With custom options
quantcoder schedule run \
  --queries "momentum,mean reversion,factor investing" \
  --min-sharpe 1.0 \
  --max-strategies 10 \
  --evolve --gens 5
```

#### Scheduled Runs

```bash
# Start daily schedule at 6 AM
quantcoder schedule start --interval daily --hour 6

# Start weekly schedule on Monday at 9 AM
quantcoder schedule start --interval weekly --day mon --hour 9

# With evolution enabled
quantcoder schedule start --interval daily --evolve --gens 5 --run-now
```

#### Check Status

```bash
quantcoder schedule status
```

---

## CLI Commands Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `quantcoder` | Launch interactive chat mode |
| `quantcoder search <query>` | Search for academic papers |
| `quantcoder download <ids>` | Download paper PDFs |
| `quantcoder summarize <id>` | Create strategy summary from paper |
| `quantcoder summaries` | List all summaries |
| `quantcoder generate <id>` | Generate QuantConnect code |
| `quantcoder validate <file>` | Validate generated code |
| `quantcoder backtest <file>` | Run backtest on QuantConnect |

### Schedule Commands

| Command | Description |
|---------|-------------|
| `quantcoder schedule start` | Start scheduled pipeline |
| `quantcoder schedule run` | Run pipeline once |
| `quantcoder schedule status` | Show scheduler status |
| `quantcoder schedule config` | Configure integrations |

### Evolution Commands

| Command | Description |
|---------|-------------|
| `quantcoder evolve start <file>` | Start evolution from code file |
| `quantcoder evolve list` | List saved evolutions |
| `quantcoder evolve show <id>` | Show evolution details |
| `quantcoder evolve export <id>` | Export best variant |

### Autonomous Mode Commands

| Command | Description |
|---------|-------------|
| `quantcoder auto start` | Start autonomous mode |
| `quantcoder auto status` | Show learning statistics |
| `quantcoder auto report` | Generate learning report |

### Logging Commands

| Command | Description |
|---------|-------------|
| `quantcoder logs show` | Show recent log entries |
| `quantcoder logs list` | List all log files |
| `quantcoder logs clear` | Clear old log files |
| `quantcoder logs config` | Configure logging settings |

---

## Configuration

Configuration is stored in `~/.quantcoder/config.toml`:

```toml
[model]
provider = "anthropic"  # anthropic, openai, mistral, deepseek, ollama
model = "claude-sonnet-4-5-20250929"
temperature = 0.5
max_tokens = 3000

[ui]
theme = "monokai"
auto_approve = false
show_token_usage = true
editor = "zed"  # zed, code, vim, etc.

[tools]
enabled_tools = ["*"]
disabled_tools = []
downloads_dir = "downloads"
generated_code_dir = "generated_code"

[logging]
level = "INFO"           # DEBUG, INFO, WARNING, ERROR
format = "standard"      # standard, json
max_file_size_mb = 10
backup_count = 5
alert_on_error = false
webhook_url = ""         # For Slack/Discord alerts
```

---

## Logging & Monitoring

### Log Files

Logs are stored in `~/.quantcoder/logs/`:

| File | Format | Purpose |
|------|--------|---------|
| `quantcoder.log` | Human-readable | Console-style logs |
| `quantcoder.json.log` | JSON | Structured logs for parsing |
| `quantcoder.log.1` | Rotated | Backup files |

### View Logs

```bash
# Show recent entries
quantcoder logs show

# Show more entries
quantcoder logs show --lines 100

# Show JSON structured logs
quantcoder logs show --json

# List all log files
quantcoder logs list
```

### Configure Logging

```bash
# Show current config
quantcoder logs config --show

# Set log level
quantcoder logs config --level DEBUG

# Configure rotation
quantcoder logs config --max-size 20 --backups 10

# Enable webhook alerts
quantcoder logs config --webhook https://hooks.slack.com/services/xxx
```

### Webhook Alerts

Set `QUANTCODER_WEBHOOK_URL` or use `--webhook` to receive alerts on ERROR/CRITICAL events.

Payload format:
```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "level": "ERROR",
  "logger": "quantcoder.scheduler.runner",
  "message": "Pipeline failed",
  "module": "runner",
  "function": "run_pipeline"
}
```

### AutoStats Persistence

Autonomous mode statistics are persisted to `~/.quantcoder/stats/`:

```bash
# View stats
quantcoder auto status

# Generate report
quantcoder auto report --format json
```

---

## Deep Search with Tavily

Traditional keyword search (CrossRef) may miss relevant papers. Deep search uses Tavily's semantic search + LLM filtering.

### Setup

```bash
# Get API key from https://tavily.com
quantcoder schedule config --tavily-key tvly-xxx
```

### Usage

```bash
# Semantic deep search
quantcoder search "pairs trading with cointegration" --deep

# With more results
quantcoder search "factor investing" --deep --num 10

# Skip LLM filtering (faster, more results)
quantcoder search "momentum" --deep --no-filter
```

### How It Works

```
Query → Tavily Semantic Search → Academic Filters (arxiv, ssrn, etc.)
      → LLM Relevance Check → Implementable Strategies Only
```

The LLM filter removes papers that:
- Are purely theoretical with no trading application
- Lack actionable entry/exit signals
- Are surveys or meta-analyses without novel strategies

---

## Strategy Evolution

AlphaEvolve-inspired optimization that uses LLM-generated mutations instead of parameter grid search.

### Start Evolution

```bash
# From generated code
quantcoder evolve start ./generated_code/strategy_1.py

# With options
quantcoder evolve start strategy.py \
  --generations 10 \
  --variants 5 \
  --start-date 2019-01-01 \
  --end-date 2024-01-01
```

### Or Integrate with Generate

```bash
# Generate → Backtest → Evolve → Publish
quantcoder generate 1 --backtest --evolve --gens 5 --variants 3
```

### Evolution Process

1. **Initial Population**: Start with base strategy
2. **Variation**: LLM generates N variants per generation
3. **Evaluation**: Backtest each variant on QuantConnect
4. **Selection**: Keep elite performers
5. **Mutation**: Apply targeted improvements
6. **Repeat**: Until convergence or max generations

### Manage Evolutions

```bash
# List all evolutions
quantcoder evolve list

# Show details
quantcoder evolve show evo_20260128_123456

# Export best variant
quantcoder evolve export evo_20260128_123456 --output best_strategy.py
```

---

## Notion Integration

Publish successful strategies as formatted articles in your Notion database.

### Setup

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Share your database with the integration
3. Configure QuantCoder:

```bash
quantcoder schedule config \
  --notion-key secret_xxx \
  --notion-db your_database_id
```

### Automatic Publishing

Strategies are published when:
- Backtest Sharpe ratio >= `min_sharpe` (default: 0.5)
- Using `--backtest` flag with `generate` command
- Or running scheduled pipeline

### Article Format

Published articles include:

| Section | Content |
|---------|---------|
| Title | Performance-based title (e.g., "High-Performance Momentum Strategy") |
| Paper Reference | Original paper title, URL, authors |
| Strategy Summary | Extracted strategy description |
| Backtest Results | Sharpe, returns, drawdown, win rate |
| Code Snippet | First 2000 chars of generated code |
| Tags | Strategy type (momentum, mean_reversion, etc.) |

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude models) |
| `OPENAI_API_KEY` | OpenAI API key (alternative) |

### QuantConnect

| Variable | Description |
|----------|-------------|
| `QUANTCONNECT_API_KEY` | QuantConnect API key |
| `QUANTCONNECT_USER_ID` | QuantConnect user ID |
| `QC_PROJECT_ID` | Default project ID (optional) |

### Integrations

| Variable | Description |
|----------|-------------|
| `NOTION_API_KEY` | Notion integration secret |
| `NOTION_DATABASE_ID` | Target database ID |
| `TAVILY_API_KEY` | Tavily API key for deep search |

### Monitoring

| Variable | Description |
|----------|-------------|
| `QUANTCODER_WEBHOOK_URL` | Webhook URL for error alerts |

---

## Example Full Workflow

### Manual Workflow

```bash
# 1. Search for papers
quantcoder search "statistical arbitrage" --deep --num 5

# 2. Download promising papers
quantcoder download 1 2

# 3. Create summaries
quantcoder summarize 1
quantcoder summarize 2

# 4. List summaries
quantcoder summaries

# 5. Generate, backtest, evolve, and publish
quantcoder generate 1 \
  --backtest \
  --min-sharpe 1.0 \
  --evolve \
  --gens 5 \
  --open-in-editor
```

### Automated Workflow

```bash
# Configure once
quantcoder schedule config \
  --notion-key secret_xxx \
  --notion-db xxx \
  --tavily-key tvly-xxx

# Start daily automation
quantcoder schedule start \
  --interval daily \
  --hour 6 \
  --queries "momentum,mean reversion,factor investing" \
  --min-sharpe 1.0 \
  --evolve \
  --gens 5 \
  --run-now

# Monitor
quantcoder schedule status
quantcoder logs show --lines 50
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "API key not found" | Check `~/.quantcoder/.env` |
| "QuantConnect credentials not configured" | Set `QUANTCONNECT_API_KEY` and `QUANTCONNECT_USER_ID` |
| "Tavily API key not set" | Run `quantcoder schedule config --tavily-key xxx` |
| "Notion credentials not configured" | Run `quantcoder schedule config --notion-key xxx --notion-db xxx` |
| Backtest timeout | Increase timeout or simplify strategy |
| Evolution not improving | Try more generations or higher mutation rate |

### Debug Mode

```bash
# Enable verbose logging
quantcoder --verbose search "test"

# Set debug level permanently
quantcoder logs config --level DEBUG
```

### Check Logs

```bash
# View recent errors
quantcoder logs show --lines 100 | grep -i error

# View JSON logs for analysis
quantcoder logs show --json
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        QuantCoder CLI                           │
├─────────────────────────────────────────────────────────────────┤
│  Workflows                                                      │
│  ├── Spot Generation (manual)                                  │
│  └── Batch Mode (automated)                                    │
├─────────────────────────────────────────────────────────────────┤
│  Core Components                                                │
│  ├── Paper Search (CrossRef, Tavily)                           │
│  ├── PDF Processing & Summarization                            │
│  ├── Code Generation (multi-provider LLM)                      │
│  ├── Validation & Auto-refinement                              │
│  ├── QuantConnect Integration                                  │
│  └── Evolution Engine                                          │
├─────────────────────────────────────────────────────────────────┤
│  Integrations                                                   │
│  ├── Notion (article publishing)                               │
│  ├── Tavily (semantic search)                                  │
│  └── Webhooks (alerting)                                       │
├─────────────────────────────────────────────────────────────────┤
│  Monitoring                                                     │
│  ├── Structured Logging (JSON + standard)                      │
│  ├── Log Rotation                                              │
│  ├── AutoStats Persistence                                     │
│  └── Webhook Alerts                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

*Last updated: January 2026*
