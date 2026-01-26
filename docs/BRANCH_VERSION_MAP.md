# QuantCoder-CLI Branch & Version Map

**Last Updated**: 2026-01-26 (**DEFAULT BRANCH: GAMMA**)
**Repository**: SL-Mar/quantcoder-cli

## ⚡ Quick Reference

QuantCoder has **3 active branches** with **gamma as the default**:

```
gamma (2.0)   → Default branch - Latest development ⭐
main  (1.0)   → Original stable
beta  (1.1)   → Improved legacy (testing)
```

---

## 📊 Active Branches Overview

| Branch | Version | Package | Status | Use Case |
|--------|---------|---------|--------|----------|
| **gamma** ⭐ | 2.0.0-alpha.1 | `quantcoder` | 🚀 Default | Autonomous mode, library builder |
| **main** | 1.0.0 | `quantcli` | 🟢 Legacy Stable | Production, simple workflows |
| **beta** | 1.1.0-beta.1 | `quantcli` | 🧪 Testing | Improved legacy, not tested |

**Archived**: `feature/enhanced-help-command`, `revert-3-feature/enhanced-help-command`

---

## 🔍 Detailed Branch Information

### 1️⃣ main → QuantCoder 1.0 (Stable)

**Branch**: `main`
**Package**: `quantcli`
**Version**: 1.0.0
**Status**: 🟢 Production stable

#### Quick Info
```bash
git checkout main
pip install -e .
```

#### Structure
```
quantcli/
├── cli.py           # Original CLI
├── processor.py     # PDF/NLP processing
├── search.py        # Article search
└── utils.py
```

#### Features
- ✅ Basic CLI for QuantConnect algorithm generation
- ✅ PDF article processing
- ✅ NLP-based strategy extraction
- ✅ OpenAI integration
- ✅ Simple article search

#### Commands
```bash
quantcli search "momentum trading"
quantcli download 1
quantcli generate 1
```

#### Pros/Cons
**Pros**: Stable, proven, simple
**Cons**: No advanced features, basic validation

#### Who Should Use
- Production environments
- Users needing stability
- Simple single-strategy workflows
- New users learning QuantCoder

---

### 2️⃣ beta → QuantCoder 1.1 (Testing)

**Branch**: `beta` (renamed from `refactor/modernize-2025`)
**Package**: `quantcli`
**Version**: 1.1.0-beta.1
**Status**: 🧪 Beta testing (⚠️ not yet tested by maintainers)

#### Quick Info
```bash
git checkout beta
pip install -e .
```

#### Structure
```
quantcli/
├── cli.py
├── llm_client.py        # NEW: LLM abstraction
├── processor.py
├── qc_validator.py      # NEW: QuantConnect validator
├── search.py
└── utils.py

tests/                   # NEW: Test suite
└── __init__.py
```

#### Features
All 1.0 features PLUS:
- ✅ **NEW**: Comprehensive testing suite
- ✅ **NEW**: Security improvements
- ✅ **NEW**: Environment configuration
- ✅ **NEW**: LLM client abstraction
- ✅ **NEW**: QuantConnect code validator
- ✅ **NEW**: Better error handling

#### Commands
```bash
# Same as 1.0
quantcli search "query"
quantcli generate 1
```

#### Pros/Cons
**Pros**: Better quality, testing, security
**Cons**: Not yet tested in production, same architecture as 1.0

#### Who Should Use
- Users wanting improved 1.0
- Testing/QA contributors
- Gradual migration from 1.0
- Those needing better validation

#### Migration from 1.0
**Difficulty**: Easy
```bash
git checkout beta
pip install -e .
# Same commands, better internals
```

---

### 3️⃣ gamma → QuantCoder 2.0 (Alpha)

**Branch**: `gamma` (renamed from `claude/refactor-quantcoder-cli-JwrsM`)
**Package**: `quantcoder` (⚠️ **NEW PACKAGE** - different from `quantcli`)
**Version**: 2.0.0-alpha.1
**Status**: 🚀 Alpha - cutting edge

#### Quick Info
```bash
git checkout gamma
pip install -e .
```

#### Structure
```
quantcoder/
├── agents/                     # Multi-agent system
│   ├── coordinator_agent.py
│   ├── universe_agent.py
│   ├── alpha_agent.py
│   ├── risk_agent.py
│   └── strategy_agent.py
├── autonomous/                 # ⭐ Self-improving mode
│   ├── database.py
│   ├── learner.py
│   ├── prompt_refiner.py
│   └── pipeline.py
├── library/                    # ⭐ Library builder
│   ├── taxonomy.py
│   ├── coverage.py
│   └── builder.py
├── codegen/
│   └── multi_file.py
├── execution/
│   └── parallel_executor.py
├── llm/
│   └── providers.py            # Multi-LLM support
├── mcp/
│   └── quantconnect_mcp.py     # MCP integration
├── tools/
│   ├── article_tools.py
│   ├── code_tools.py
│   └── file_tools.py
├── chat.py
├── cli.py                      # Enhanced CLI
└── config.py

quantcli/                       # Legacy code (kept for reference)
docs/                           # Comprehensive documentation
```

#### Features

**Complete rewrite** with revolutionary capabilities:

**Core Architecture**:
- ✅ Tool-based design (Mistral Vibe CLI inspired)
- ✅ Multi-agent system (6 specialized agents)
- ✅ Parallel execution framework (3-5x faster)
- ✅ MCP integration for QuantConnect
- ✅ Multi-LLM support (Anthropic, Mistral, DeepSeek, OpenAI)

**🤖 Autonomous Mode** (Self-learning):
- ✅ Learns from compilation errors automatically
- ✅ Performance-based prompt refinement
- ✅ Self-healing code fixes
- ✅ Learning database (SQLite)
- ✅ Continuous improvement over iterations

**📚 Library Builder Mode**:
- ✅ Build complete strategy library from scratch
- ✅ 10 strategy categories (86 total strategies)
- ✅ Systematic coverage tracking
- ✅ Progress checkpoints & resume capability

**Advanced Features**:
- ✅ Multi-file generation (Universe, Alpha, Risk, Main)
- ✅ Coordinator agent orchestration
- ✅ Real-time learning and adaptation
- ✅ Interactive and programmatic modes
- ✅ Rich CLI with modern UI

#### Commands

**Regular Mode**:
```bash
quantcoder chat
quantcoder search "query"
quantcoder generate 1
```

**Autonomous Mode** (⭐ NEW):
```bash
quantcoder auto start --query "momentum trading" --max-iterations 50
quantcoder auto status
quantcoder auto report
```

**Library Builder** (⭐ NEW):
```bash
quantcoder library build --comprehensive --max-hours 24
quantcoder library status
quantcoder library resume
quantcoder library export --format zip
```

#### Pros/Cons
**Pros**:
- Revolutionary autonomous features
- Self-improving AI
- Can build entire libraries
- Multi-LLM flexibility
- 3-5x faster with parallel execution

**Cons**:
- Alpha status (active development)
- Breaking changes from 1.x
- Different package name
- Higher resource requirements
- More complex

#### Who Should Use
- Users wanting cutting-edge features
- Building complete strategy libraries
- Autonomous overnight generation runs
- Research and experimentation
- Advanced multi-agent workflows

#### Migration from 1.x
**Difficulty**: Moderate

**Breaking Changes**:
- Package: `quantcli` → `quantcoder`
- Commands: Different CLI interface
- Config: New format
- Dependencies: More requirements

**Steps**:
```bash
git checkout gamma
pip install -e .
quantcoder --help  # Learn new commands
```

---

## 🗺️ Version Evolution Timeline

```
2023 November
    │
    └─> QuantCoder 1.0 (main)
        └─ Original CLI, quantcli package
            │
2025 January
            │
            ├─> QuantCoder 1.1 (beta)
            │   └─ Improved legacy
            │      Testing + Security
            │      Same quantcli package
            │
            └─> QuantCoder 2.0 (gamma)
                └─ Complete rewrite
                   NEW quantcoder package
                   ├─ Multi-agent system
                   ├─ Autonomous mode ⭐
                   └─ Library builder ⭐
```

---

## 📋 Feature Comparison Matrix

| Feature | 1.0 (main) | 1.1 (beta) | 2.0 (gamma) |
|---------|------------|------------|-------------|
| **Package** | quantcli | quantcli | quantcoder |
| **Status** | Stable | Testing | Alpha |
| **Basic CLI** | ✅ | ✅ | ✅ |
| **PDF Processing** | ✅ | ✅ | ✅ |
| **Article Search** | ✅ | ✅ | ✅ |
| **Code Generation** | ✅ | ✅ | ✅ |
| **Testing Suite** | ❌ | ✅ | ⚠️ |
| **Security** | Basic | Enhanced | Enhanced |
| **Validation** | Basic | Enhanced | Advanced |
| **Tool Architecture** | ❌ | ❌ | ✅ |
| **Multi-Agent** | ❌ | ❌ | ✅ |
| **Parallel Execution** | ❌ | ❌ | ✅ |
| **MCP Integration** | ❌ | ❌ | ✅ |
| **Multi-LLM** | ❌ | ❌ | ✅ |
| **Autonomous Mode** | ❌ | ❌ | ✅ ⭐ |
| **Library Builder** | ❌ | ❌ | ✅ ⭐ |
| **Self-Learning** | ❌ | ❌ | ✅ ⭐ |

---

## 🎯 Branch Selection Guide

### Choose **main** (1.0) if:
- ✅ You need stability and proven code
- ✅ Simple single-strategy generation
- ✅ Production environment
- ✅ Learning QuantCoder
- ✅ Low resource requirements

### Choose **beta** (1.1) if:
- ✅ You want improved 1.0
- ✅ Better validation needed
- ✅ Willing to test new features
- ✅ Same familiar interface
- ⚠️ Accept untested status

### Choose **gamma** (2.0) if:
- ✅ You want cutting-edge features
- ✅ Building complete libraries
- ✅ Autonomous overnight runs
- ✅ Multi-agent workflows
- ✅ Self-improving AI
- ⚠️ Accept alpha status

---

## 📚 Documentation by Branch

### main (1.0)
- Original README
- Legacy documentation

### beta (1.1)
- Testing guide
- Security documentation
- Validation improvements

### gamma (2.0)
- [VERSION_COMPARISON.md](./VERSION_COMPARISON.md) - Choose version
- [NEW_FEATURES_V4.md](./NEW_FEATURES_V4.md) - 2.0 overview
- [AUTONOMOUS_MODE.md](./AUTONOMOUS_MODE.md) - Self-learning guide
- [LIBRARY_BUILDER.md](./LIBRARY_BUILDER.md) - Library building
- [ARCHITECTURE_V3_MULTI_AGENT.md](./ARCHITECTURE_V3_MULTI_AGENT.md) - Multi-agent

---

## 🗑️ Archived Branches

The following branches have been archived (tagged for history):

- `feature/enhanced-help-command` → Added help docs (reverted)
- `revert-3-feature/enhanced-help-command` → Revert branch

These are no longer active and can be deleted after tagging.

---

## 🔄 Restructuring Summary

**What Changed**:
- ✅ `claude/refactor-quantcoder-cli-JwrsM` → `gamma` (2.0)
- ✅ `refactor/modernize-2025` → `beta` (1.1)
- ✅ `main` stays as 1.0
- ✅ Version numbering: v4.0 → 2.0.0-alpha.1
- ✅ Clear progression: 1.0 → 1.1 → 2.0

**Why**:
- Clear version semantics (1.x = legacy, 2.x = rewrite)
- Proper semantic versioning
- Easy branch selection for users
- Clean repository with 3 active branches

---

## ❓ FAQ

**Q: Why is 2.0 called "gamma" not "v2"?**
A: Greek letters indicate progression: alpha → beta → gamma. Shows 2.0 is beyond beta (1.1).

**Q: What happened to v3.0 and v4.0?**
A: Renumbered to 2.0.0-alpha.1 since it's the first major rewrite.

**Q: Can I use both quantcli and quantcoder?**
A: Yes! Different packages, no conflicts.

**Q: Which branch gets updates?**
A: All three are maintained. Critical bugs fixed in all. New features in 2.0.

**Q: When will 2.0 be stable?**
A: After alpha → beta → release candidate → 2.0.0 stable.

---

## 📞 Support

- **Issues**: Open issue and specify branch (1.0/1.1/2.0)
- **Questions**: Specify which version you're using
- **Contributions**: See CONTRIBUTING.md

---

**Last Restructured**: 2025-01-15
**Maintained by**: SL-MAR
**Repository**: SL-Mar/quantcoder-cli
