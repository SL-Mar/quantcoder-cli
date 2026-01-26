# QuantCoder CLI - Version Guide

This document describes the available versions of QuantCoder CLI and their features.

---

## Version Overview

| Version | Branch | Status | Package | Key Features |
|---------|--------|--------|---------|--------------|
| **v1.0** | `main` | Released | `quantcli` | Legacy, basic features |
| **v1.1** | `beta` | Released | `quantcli` | LLM abstraction, static validator |
| **v2.0** | `develop` | In Development | `quantcoder` | Multi-agent, autonomous |

---

## v1.0 - Legacy Release

**Tag:** `v1.0`
**Branch:** `main`
**Package:** `quantcli`

### Features

- Search academic articles via CrossRef API
- Download PDFs via direct links or Unpaywall API
- Extract trading strategies using NLP (spaCy)
- Generate QuantConnect algorithms using OpenAI GPT-4
- Tkinter GUI for interactive workflow
- Basic AST code validation with refinement loop

### Dependencies

- Python 3.8+
- OpenAI SDK v0.28 (legacy)
- pdfplumber, spaCy (en_core_web_sm)
- Click CLI framework
- Tkinter (built-in)

### Installation

```bash
git checkout v1.0
pip install -e .
```

### Usage

```bash
quantcli search "momentum trading"
quantcli download 1
quantcli summarize 1
quantcli generate-code 1
quantcli interactive  # Launch GUI
```

### Limitations

- Single LLM provider (OpenAI only)
- Legacy OpenAI SDK (v0.28)
- No runtime safety validation
- Single-file code generation

---

## v1.1 - Enhanced Release

**Tag:** `v1.1`
**Branch:** `beta`
**Package:** `quantcli`

### What's New in v1.1

- **LLM Client Abstraction**: Modern OpenAI SDK v1.x+ support
- **QC Static Validator**: Catches runtime errors before execution
- **Improved Prompts**: Defensive programming patterns in generated code
- **Unit Tests**: Test coverage for LLM client
- **Better Documentation**: Testing guide, changelog

### Features

All v1.0 features plus:

- `LLMClient` class with standardized response handling
- `QuantConnectValidator` for static code analysis:
  - Division by zero detection
  - Missing `.IsReady` checks on indicators
  - `None` value risk detection
  - `max()/min()` on potentially None values
- Enhanced code generation prompts with runtime safety requirements
- Token usage tracking in LLM responses

### Dependencies

- Python 3.8+
- OpenAI SDK v1.x+ (modern)
- All v1.0 dependencies

### Installation

```bash
git checkout v1.1
pip install -e .
```

### Usage

Same as v1.0:

```bash
quantcli search "mean reversion"
quantcli download 1
quantcli generate-code 1
```

### Breaking Changes from v1.0

- Requires OpenAI SDK v1.x+ (not compatible with v0.28)
- Environment variable `OPENAI_API_KEY` required

---

## v2.0 - Next Generation (In Development)

**Branch:** `develop`
**Package:** `quantcoder`

### Major Architectural Changes

Complete rewrite with enterprise-grade features:

- **Multi-Agent System**: Specialized agents for different tasks
  - `CoordinatorAgent`: Orchestrates workflow
  - `UniverseAgent`: Stock selection logic
  - `AlphaAgent`: Trading signal generation
  - `RiskAgent`: Position sizing and risk management
  - `StrategyAgent`: Integration into Main.py

- **Multi-File Code Generation**: Generates separate files
  - `Main.py` - Main algorithm
  - `Alpha.py` - Alpha model
  - `Universe.py` - Universe selection
  - `Risk.py` - Risk management

- **Autonomous Pipeline**: Self-improving strategy generation
  - Error learning and pattern extraction
  - Performance-based prompt refinement
  - Continuous iteration with quality gates

- **Library Builder**: Batch strategy generation
  - 13+ strategy categories
  - Checkpointing and resume
  - Coverage tracking

- **Multi-LLM Support**: Provider abstraction
  - OpenAI (GPT-4)
  - Anthropic (Claude)
  - Mistral
  - DeepSeek

- **Modern CLI**: Rich terminal interface
  - Interactive REPL with history
  - Syntax highlighting
  - Progress indicators

### Installation (Development)

```bash
git checkout develop
pip install -e ".[dev]"
```

### Usage

```bash
# Interactive mode
quantcoder

# Programmatic mode
quantcoder --prompt "Create momentum strategy"

# Direct commands
quantcoder search "pairs trading"
quantcoder generate 1

# Autonomous mode
quantcoder auto start --query "momentum" --max-iterations 50

# Library builder
quantcoder library build --comprehensive
```

### Status

🚧 **In Development** - Not ready for production use.

---

## Upgrade Path

```
v1.0 ──────▶ v1.1 ──────▶ v2.0
     Minor        Major
     (safe)      (breaking)
```

### v1.0 → v1.1

- Update OpenAI SDK: `pip install openai>=1.0.0`
- No code changes required for CLI usage
- Benefits: Better error handling, runtime validation

### v1.1 → v2.0

- Package renamed: `quantcli` → `quantcoder`
- New architecture (multi-agent)
- New CLI commands
- Requires migration of custom scripts

---

## Choosing a Version

| Use Case | Recommended Version |
|----------|---------------------|
| Quick start, simple needs | v1.0 |
| Production with validation | v1.1 |
| Multiple strategies at scale | v2.0 (when ready) |
| Research and experimentation | v2.0 develop |

---

## Version Comparison

| Feature | v1.0 | v1.1 | v2.0 |
|---------|------|------|------|
| CrossRef Search | ✓ | ✓ | ✓ |
| PDF Download | ✓ | ✓ | ✓ |
| NLP Extraction | ✓ | ✓ | ✓ |
| Code Generation | Single file | Single file | Multi-file |
| AST Validation | ✓ | ✓ | ✓ |
| Runtime Validator | ✗ | ✓ | ✓ + MCP |
| LLM Providers | OpenAI only | OpenAI (v1.x) | Multi-provider |
| Tkinter GUI | ✓ | ✓ | ✗ |
| Rich Terminal | ✗ | ✗ | ✓ |
| Multi-Agent | ✗ | ✗ | ✓ |
| Autonomous Mode | ✗ | ✗ | ✓ |
| Library Builder | ✗ | ✗ | ✓ |
| Self-Learning | ✗ | ✗ | ✓ |

---

## Support

- **v1.0**: Maintenance only (critical fixes)
- **v1.1**: Active support
- **v2.0**: Development preview
