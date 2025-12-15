# Complete Branch & Version Comparison

**Date**: 2025-12-15
**Repository**: SL-Mar/quantcoder-cli

## 🎯 Quick Decision Guide

| What you need | Use this branch |
|---------------|----------------|
| **Stable, tested, legacy** | `main` (v0.3) |
| **Modernized with OpenAI SDK 1.x** | `beta` (v1.0.0) |
| **AI assistant, autonomous mode** | `gamma` (v2.0.0) |

---

## 📊 Branch Comparison Table

| Feature | main | beta | gamma |
|---------|------|------|-------|
| **Package Name** | `quantcli` | `quantcli` | `quantcoder` |
| **Version** | 0.3 | 1.0.0 | 2.0.0-alpha.1 |
| **Last Update** | Dec 2024 | Dec 2025 | Dec 2025 |
| **Python Required** | ≥3.8 | ≥3.9 | ≥3.10 |
| **OpenAI SDK** | 0.28 (legacy) | 1.x (modern) | 1.x (modern) |
| **Packaging** | setup.py | setup.py | pyproject.toml |
| **Command** | `quantcli` | `quantcli` | `quantcoder` or `qc` |
| **Total Code** | ~1,426 lines | ~1,874 lines | ~10,000+ lines |

---

## 🔍 Detailed Comparison

### 📦 MAIN Branch (v0.3)

**Status**: 🟢 Stable Legacy
**Package**: `quantcli`
**Last Commit**: `f4b4674 - Update project title in README.md`

#### Structure
```
quantcli/
├── __init__.py (empty)
├── cli.py          (217 lines) - Basic Click CLI
├── gui.py          (344 lines) - Tkinter GUI
├── processor.py    (641 lines) - PDF/NLP processing
├── search.py       (109 lines) - CrossRef search
└── utils.py        (115 lines) - Utilities
```

#### Features
- ✅ Basic CLI commands (search, download, summarize, generate-code)
- ✅ CrossRef article search
- ✅ PDF processing with pdfplumber
- ✅ NLP with spacy
- ✅ Tkinter GUI (interactive mode)
- ✅ OpenAI GPT integration (SDK 0.28)
- ❌ No enhanced help (was reverted)
- ❌ Old OpenAI SDK
- ❌ No modern features

#### Dependencies
- OpenAI SDK 0.28 (old)
- Click, requests, pdfplumber, spacy
- InquirerPy, pygments

#### Use Case
- **Legacy projects** requiring old OpenAI SDK
- **Proven stable** version
- **Simple workflows**

---

### 📦 BETA Branch (v1.0.0)

**Status**: 🧪 Testing (Modernized)
**Package**: `quantcli`
**Last Commit**: `9a5f173 - Merge pull request #7`

#### Structure
```
quantcli/
├── __init__.py (empty)
├── cli.py          (235 lines) - Click CLI
├── gui.py          (349 lines) - Tkinter GUI (lazy imports)
├── llm_client.py   (138 lines) - ✨ NEW: LLM client abstraction
├── processor.py    (691 lines) - Enhanced processing
├── qc_validator.py (202 lines) - ✨ NEW: QuantConnect validator
├── search.py       (109 lines) - CrossRef search
└── utils.py        (150 lines) - Enhanced utilities
```

#### Features
- ✅ All main branch features
- ✅ **OpenAI SDK 1.x** (modern)
- ✅ **LLM client abstraction** (supports multiple providers)
- ✅ **QuantConnect code validator**
- ✅ **Lazy GUI imports** (no tkinter errors)
- ✅ **Improved error handling**
- ✅ **Better logging**
- ❌ Still basic CLI (no AI assistant mode)

#### New Files
- `llm_client.py`: Abstraction for OpenAI/Anthropic/local models
- `qc_validator.py`: Validates generated QuantConnect code

#### Use Case
- **Modern OpenAI SDK** compatibility
- **Better than main** but same workflow
- **Not yet tested** by user

---

### 📦 GAMMA Branch (v2.0.0-alpha.1)

**Status**: 🚀 Alpha (Complete Rewrite)
**Package**: `quantcoder`
**Last Commit**: `1b7cea5 - Add mobile-friendly branch reorganization tools`

#### Structure
```
quantcoder/
├── __init__.py          - Version 2.0.0-alpha.1
├── cli.py               - Modern CLI with subcommands
├── chat.py              - Interactive chat interface
├── config.py            - TOML configuration system
├── agents/              - Multi-agent architecture
│   ├── base.py
│   ├── coordinator.py
│   ├── universe.py
│   ├── alpha.py
│   ├── risk.py
│   └── strategy.py
├── autonomous/          - 🤖 Self-learning system
│   ├── database.py      - Learning database (SQLite)
│   ├── learner.py       - Error & performance learning
│   ├── pipeline.py      - Autonomous orchestration
│   └── prompt_refiner.py - Dynamic prompt enhancement
├── library/             - 📚 Strategy library builder
│   ├── taxonomy.py      - 10 categories, 86 strategies
│   ├── coverage.py      - Progress tracking
│   └── builder.py       - Systematic building
├── codegen/             - Code generation
├── core/                - Core utilities
├── execution/           - Parallel execution (AsyncIO)
├── llm/                 - LLM providers (OpenAI, Anthropic, Mistral)
├── mcp/                 - Model Context Protocol
└── tools/               - CLI tools
```

#### Features

**🎨 Modern Architecture**
- ✅ **Vibe CLI-inspired** design (Mistral)
- ✅ **Interactive chat** interface
- ✅ **Tool-based architecture**
- ✅ **TOML configuration**
- ✅ **Rich terminal UI**
- ✅ **Persistent context**

**🤖 AI Assistant**
- ✅ **Multi-agent system** (6 specialized agents)
- ✅ **Parallel execution** (AsyncIO, 3-5x faster)
- ✅ **Conversational interface**
- ✅ **Context-aware responses**

**🧠 Autonomous Mode** (NEW!)
- ✅ **Self-learning** from errors
- ✅ **Performance analysis**
- ✅ **Auto-fix compilation** errors
- ✅ **Prompt refinement** based on learnings
- ✅ **SQLite database** for learnings
- ✅ **Success rate** improves over time (50% → 85%)

**📚 Library Builder** (NEW!)
- ✅ **10 strategy categories**
- ✅ **86 strategies** (target)
- ✅ **Systematic coverage**
- ✅ **Priority-based** building
- ✅ **Checkpoint/resume**
- ✅ **Progress tracking**

**🔧 Advanced Features**
- ✅ **MCP integration** (QuantConnect)
- ✅ **Multi-provider LLMs** (OpenAI, Anthropic, Mistral)
- ✅ **Comprehensive testing**
- ✅ **Modern packaging** (pyproject.toml)

#### Commands
```bash
# Chat mode
quantcoder chat "Create momentum strategy"

# Autonomous mode
quantcoder auto start "momentum trading" --max-iterations 50

# Library builder
quantcoder library build --comprehensive

# Regular commands (like old CLI)
quantcoder search "pairs trading"
quantcoder generate <article-id>
```

#### Use Case
- **AI-powered** strategy generation
- **Autonomous learning** systems
- **Library building** from scratch
- **Research & experimentation**
- **Cutting edge** features

---

## 🌿 Archive Branches

These are **not main development branches**:

### feature/enhanced-help-command
- **Purpose**: Enhanced `--help` documentation + `--version` flag
- **Status**: ✅ Feature complete, ❌ Reverted from main
- **Use**: Can be re-merged if needed

### revert-3-feature/enhanced-help-command
- **Purpose**: Revert PR for enhanced help
- **Status**: Already merged to main
- **Use**: Historical record only

### claude/gamma-docs-update-JwrsM
- **Purpose**: Documentation cleanup for gamma
- **Status**: Temporary branch, ready to merge
- **Use**: Merge into gamma when ready

### claude/re-add-enhanced-help-JwrsM
- **Purpose**: Re-add enhanced help to main
- **Status**: Ready to merge
- **Use**: Merge into main if enhanced help is wanted

---

## 📈 Migration Paths

### From main → beta
**Reason**: Modernize to OpenAI SDK 1.x

```bash
# Update code
git checkout beta

# Update dependencies
pip install -e .

# Update .env if needed
OPENAI_API_KEY=sk-...

# Test
quantcli search "test"
```

**Breaking Changes**:
- OpenAI SDK 0.28 → 1.x (API changed)
- Python 3.8 → 3.9 minimum

### From main/beta → gamma
**Reason**: Get AI assistant + autonomous mode

```bash
# New package name!
git checkout gamma

# Install
pip install -e .

# Configure
quantcoder config

# Try chat mode
quantcoder chat "Create a momentum strategy"
```

**Breaking Changes**:
- Package name: `quantcli` → `quantcoder`
- Command name: `quantcli` → `quantcoder` or `qc`
- Python 3.9 → 3.10 minimum
- Completely different CLI interface
- New TOML config system

---

## 🎯 Recommendations

### For Production Use
→ **main** (v0.3)
Most stable, proven, but old SDK

### For Modern SDK
→ **beta** (v1.0.0)
Same workflow, updated dependencies

### For AI Features
→ **gamma** (v2.0.0-alpha.1)
Complete rewrite, autonomous mode, library builder

---

## 📊 Version History

```
main (0.3)
   ↓
beta (1.0.0) ← Modernize OpenAI SDK, add validators
   ↓
gamma (2.0.0-alpha.1) ← Complete rewrite, AI assistant
```

---

## 🔧 Current Issues

### All Branches
- ❌ 75 dependency vulnerabilities (GitHub Dependabot alert)
  - 4 critical, 29 high, 33 moderate, 9 low
  - Should be addressed across all branches

### main
- ❌ Enhanced help was reverted (basic help only)
- ❌ Old OpenAI SDK (0.28)

### beta
- ⚠️ Not tested by user yet
- ⚠️ Version says 1.0.0 but documentation says 1.1.0-beta.1

### gamma
- ⚠️ Alpha quality (testing phase)
- ⚠️ Version mismatch: pyproject.toml says 2.0.0, __init__.py says 2.0.0-alpha.1
- ⚠️ Old setup.py still exists (should remove, use pyproject.toml only)

---

## ✅ Next Steps

1. **Fix version inconsistencies** in gamma
2. **Remove old setup.py** from gamma (use pyproject.toml)
3. **Address security vulnerabilities** across all branches
4. **Test beta** branch thoroughly
5. **Decide on enhanced help** for main (merge or leave reverted)
6. **Archive feature branches** that are no longer needed

---

**Generated**: 2025-12-15
**Tool**: Claude Code
**Repository**: https://github.com/SL-Mar/quantcoder-cli
