# QuantCoder-CLI Branch & Version Map

**Last Updated**: 2025-01-15
**Repository**: SL-Mar/quantcoder-cli

This document maps all branches in the repository and their respective versions/features.

---

## 📊 Overview Table

| Branch | Version | Package | Status | Key Features | Latest Commit |
|--------|---------|---------|--------|--------------|---------------|
| **main** | Legacy | `quantcli` | 🟢 Stable | Original CLI | f4b4674 |
| **claude/refactor-quantcoder-cli-JwrsM** | v4.0 | `quantcoder` | 🟢 Active Dev | Multi-Agent + Autonomous + Library | ddabcc1 |
| **refactor/modernize-2025** | v1.0 | `quantcli` | 🟡 Modernized | Testing + Security | 9a5f173 |
| **feature/enhanced-help-command** | Legacy+ | `quantcli` | 🔴 Reverted | Enhanced help | af9e399 |
| **revert-3-feature/enhanced-help-command** | Legacy | `quantcli` | 🔴 Revert | Reverts help | 4f9e253 |

---

## 🔍 Detailed Branch Analysis

### 1️⃣ **main** (Stable Legacy)

**Package**: `quantcli`
**Version**: Original/Legacy
**Status**: 🟢 Stable, production legacy version

#### Structure
```
quantcli/
├── __init__.py
├── cli.py          # Original CLI
├── gui.py
├── processor.py    # PDF/NLP processing
├── search.py       # Article search
└── utils.py
```

#### Features
- ✅ Basic CLI for generating QuantConnect algorithms
- ✅ PDF article processing
- ✅ NLP-based strategy extraction
- ✅ OpenAI integration
- ✅ Simple search functionality

#### Commits (Recent)
```
f4b4674 Update project title in README.md
a91fdbe Revise README for legacy CLI version status
3b0608f Merge pull request #4 from SL-Mar/revert-3-feature/enhanced-help-command
4f9e253 Revert "Add comprehensive --help documentation and --version flag"
```

#### Use Case
- Legacy production version
- Basic single-strategy generation
- Simple workflow: search → download → generate

---

### 2️⃣ **claude/refactor-quantcoder-cli-JwrsM** (v4.0 - Current Development)

**Package**: `quantcoder` (NEW)
**Version**: v4.0 (Multi-Agent + Autonomous)
**Status**: 🟢 Active development, feature-complete

#### Structure
```
quantcoder/
├── agents/                    # v3.0: Multi-Agent System
│   ├── base.py
│   ├── coordinator_agent.py
│   ├── universe_agent.py
│   ├── alpha_agent.py
│   ├── risk_agent.py
│   └── strategy_agent.py
├── autonomous/                # v4.0: NEW - Self-improving mode
│   ├── database.py
│   ├── learner.py
│   ├── prompt_refiner.py
│   └── pipeline.py
├── library/                   # v4.0: NEW - Library builder
│   ├── taxonomy.py
│   ├── coverage.py
│   └── builder.py
├── codegen/
│   └── multi_file.py
├── execution/
│   └── parallel_executor.py
├── llm/
│   └── providers.py          # Multi-LLM support
├── mcp/
│   └── quantconnect_mcp.py   # MCP integration
├── tools/                     # v2.0: Tool-based architecture
│   ├── article_tools.py
│   ├── code_tools.py
│   └── file_tools.py
├── chat.py
├── cli.py                     # Enhanced with auto/library commands
└── config.py

quantcli/                      # Legacy code still present
└── ... (original files)

docs/
├── ARCHITECTURE_V3_MULTI_AGENT.md
├── AGENTIC_WORKFLOW.md
├── AUTONOMOUS_MODE.md         # v4.0 docs
├── LIBRARY_BUILDER.md         # v4.0 docs
└── NEW_FEATURES_V4.md         # v4.0 docs
```

#### Features

**v2.0 Features** (Vibe CLI-inspired):
- ✅ Tool-based architecture
- ✅ Interactive & programmatic chat modes
- ✅ Rich CLI with modern UI
- ✅ Article search/download/summarize tools
- ✅ Code generation with validation

**v3.0 Features** (Claude Code-inspired):
- ✅ Multi-agent system (6 specialized agents)
- ✅ Parallel execution framework
- ✅ MCP integration for QuantConnect
- ✅ Multi-file generation (Universe, Alpha, Risk, Main)
- ✅ Multi-LLM support (Anthropic, Mistral, DeepSeek, OpenAI)
- ✅ Coordinator orchestration

**v4.0 Features** (NEW):
- ✅ **Autonomous Mode**: Self-improving strategy generation
  - Learning database (SQLite)
  - Error pattern recognition
  - Performance-based learning
  - Prompt evolution
  - Self-healing code fixes
- ✅ **Library Builder Mode**: Complete library from scratch
  - 10 strategy categories
  - 86 target strategies
  - Systematic coverage
  - Progress tracking & checkpoints
  - Resume capability

#### CLI Commands

**Regular Mode (v2.0)**:
```bash
quantcoder chat
quantcoder search "query"
quantcoder generate 1
```

**Autonomous Mode (v4.0)**:
```bash
quantcoder auto start --query "momentum trading"
quantcoder auto status
quantcoder auto report
```

**Library Builder (v4.0)**:
```bash
quantcoder library build --comprehensive
quantcoder library status
quantcoder library resume
quantcoder library export
```

#### Commits (Recent)
```
ddabcc1 Add Autonomous Mode and Library Builder - v4.0 🚀
25f5a2b Complete Multi-Agent System v3.0 - Production Ready! 🚀
32c1f11 Implement Multi-Agent Architecture v3.0 - Foundation
7310aad Add HTML version for easy Notion import
5bad91a Add process-oriented agentic workflow explanation
```

#### Use Case
- Advanced multi-agent strategy generation
- Self-improving autonomous loops
- Building complete strategy libraries
- Production-ready algorithm development

---

### 3️⃣ **refactor/modernize-2025** (v1.0 Modernized)

**Package**: `quantcli`
**Version**: v1.0 (Modernized Legacy)
**Status**: 🟡 Modernized with testing/security

#### Structure
```
quantcli/
├── __init__.py
├── cli.py
├── gui.py
├── llm_client.py        # NEW: Abstracted LLM client
├── processor.py
├── qc_validator.py      # NEW: QuantConnect validator
├── search.py
└── utils.py

tests/                   # NEW: Test suite
└── __init__.py
```

#### Features
- ✅ Original CLI functionality
- ✅ **NEW**: Comprehensive testing
- ✅ **NEW**: Security improvements
- ✅ **NEW**: Environment configuration
- ✅ **NEW**: LLM client abstraction
- ✅ **NEW**: QuantConnect validator

#### Commits (Recent)
```
9a5f173 Merge pull request #7 from SL-Mar/claude/refactor-modernize-2025-011CV1sadPRrxj5sPHjWp7Wa
de7eac0 Merge branch 'main' into refactor/modernize-2025
79e8626 Add comprehensive testing guide for v1.0.0
9fc699a Add security improvements and environment configuration
```

#### Use Case
- Modernized legacy code
- Better testing coverage
- Improved security
- Bridge between legacy and v2.0+

---

### 4️⃣ **feature/enhanced-help-command** (Reverted)

**Package**: `quantcli`
**Version**: Legacy + Help
**Status**: 🔴 Reverted (not in main)

#### Features
- ✅ Original CLI
- ✅ Enhanced `--help` documentation
- ✅ `--version` flag

#### Commits
```
af9e399 Add comprehensive --help documentation and --version flag
5170f19 Delete quantcli.egg-info directory
5434ea9 Delete build directory
```

#### Note
This branch was merged then reverted. Features not in main.

---

### 5️⃣ **revert-3-feature/enhanced-help-command** (Revert Branch)

**Package**: `quantcli`
**Version**: Legacy
**Status**: 🔴 Revert branch

#### Purpose
Branch created to revert the enhanced-help-command feature.

#### Commits
```
4f9e253 Revert "Add comprehensive --help documentation and --version flag"
```

---

## 🗺️ Version Evolution

```
Legacy (main)
    │
    ├─> v1.0 (refactor/modernize-2025)
    │   └─> Testing + Security
    │
    └─> v2.0 (claude/refactor-quantcoder-cli-JwrsM)
        └─> Tool-based architecture (Vibe CLI)
            │
            └─> v3.0
                └─> Multi-Agent System (Claude Code)
                    │
                    └─> v4.0 ⭐ CURRENT
                        ├─> Autonomous Mode
                        └─> Library Builder
```

---

## 📦 Package Comparison

### `quantcli` (Legacy Package)
**Used by**: main, refactor/modernize-2025, feature branches

**Characteristics**:
- Original codebase from 2023
- Single CLI entry point
- Monolithic structure
- Basic functionality

### `quantcoder` (New Package)
**Used by**: claude/refactor-quantcoder-cli-JwrsM

**Characteristics**:
- Complete rewrite (v2.0+)
- Modular architecture
- Multi-agent system
- Advanced features (autonomous, library builder)
- Tool-based design

---

## 🎯 Feature Matrix

| Feature | main | modernize-2025 | v4.0 (claude) |
|---------|------|----------------|---------------|
| Basic CLI | ✅ | ✅ | ✅ |
| PDF Processing | ✅ | ✅ | ✅ |
| Article Search | ✅ | ✅ | ✅ |
| Code Generation | ✅ | ✅ | ✅ |
| Testing Suite | ❌ | ✅ | ⚠️ |
| Security Hardening | ❌ | ✅ | ⚠️ |
| Tool-based Architecture | ❌ | ❌ | ✅ |
| Multi-Agent System | ❌ | ❌ | ✅ |
| Parallel Execution | ❌ | ❌ | ✅ |
| MCP Integration | ❌ | ❌ | ✅ |
| Multi-LLM Support | ❌ | ❌ | ✅ |
| **Autonomous Mode** | ❌ | ❌ | ✅ |
| **Library Builder** | ❌ | ❌ | ✅ |
| Self-Learning | ❌ | ❌ | ✅ |

---

## 🚀 Recommended Merge Strategy

### Option 1: Keep Separate (Recommended)
```
main (quantcli)           → Legacy version for production
└─> v1.0 modernize-2025   → Improved legacy

claude/refactor (quantcoder) → New architecture (v2.0-v4.0)
```

**Pros**:
- No breaking changes
- Users can choose version
- Legacy remains stable

**Cons**:
- Two codebases to maintain

### Option 2: Replace Main
```
main → Deprecate quantcli
└─> Point to claude/refactor as new main
```

**Pros**:
- Single codebase
- Modern architecture

**Cons**:
- Breaking changes for existing users
- Migration effort

### Option 3: Parallel Development
```
main (quantcli-legacy)       → v1.x line
claude/refactor (quantcoder) → v2.x+ line
```

**Pros**:
- Both active
- Clear versioning

**Cons**:
- Duplicate maintenance

---

## 📝 Branch Recommendations

### Active Development
- ✅ **claude/refactor-quantcoder-cli-JwrsM**: Continue as v4.0+
  - Most advanced features
  - Self-improving capabilities
  - Complete library building

### Maintenance
- ✅ **main**: Keep as legacy stable release
  - Simple use cases
  - Existing user base

### Consider Merging
- 🔄 **refactor/modernize-2025** → Could merge improvements into main
  - Testing suite
  - Security enhancements
  - Better structure

### Archive/Delete
- 🗑️ **feature/enhanced-help-command**: Already reverted
- 🗑️ **revert-3-feature/enhanced-help-command**: Served its purpose

---

## 🏷️ Tagging Recommendation

**Current Tags**: v0.3

**Suggested Tags**:
```
v0.3   → main (current legacy)
v1.0.0 → refactor/modernize-2025 (modernized legacy)
v2.0.0 → claude/refactor (tool-based)
v3.0.0 → claude/refactor (multi-agent)
v4.0.0 → claude/refactor (autonomous + library) ⭐
```

---

## 🎓 Summary

### For Users:

**Want simple, stable CLI?**
→ Use **main** branch (`quantcli`)

**Want modernized legacy with tests?**
→ Use **refactor/modernize-2025** (`quantcli` v1.0)

**Want advanced multi-agent system?**
→ Use **claude/refactor-quantcoder-cli-JwrsM** (`quantcoder` v3.0)

**Want autonomous library building?**
→ Use **claude/refactor-quantcoder-cli-JwrsM** (`quantcoder` v4.0) ⭐

### For Maintainers:

**Priority 1**: Continue v4.0 development on `claude/refactor-quantcoder-cli-JwrsM`
**Priority 2**: Decide on main vs modernize-2025 merge
**Priority 3**: Tag releases appropriately
**Priority 4**: Archive feature/revert branches

---

**Generated by**: Claude
**Date**: 2025-01-15
**Branch**: claude/refactor-quantcoder-cli-JwrsM
**Commit**: ddabcc1
