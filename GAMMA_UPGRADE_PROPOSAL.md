# Gamma Branch Upgrade Proposal

**Date:** 2026-01-25
**Author:** Claude
**Current Branch:** `claude/cli-zed-integration-mRF07`

---

## Executive Summary

After analyzing all 17 branches in the quantcoder-cli repository, this document proposes a prioritized list of upgrades for the gamma branch (v2.0.0-alpha.1). The gamma branch already scores 88% on production readiness - these upgrades would bring it to production quality.

---

## Branch Analysis Summary

| Branch | Type | Key Features | Lines Changed | Merge Priority |
|--------|------|--------------|---------------|----------------|
| `claude/wire-mcp-production-mRF07` | Feature | MCP wiring for backtest/validate | +459 | **HIGH** |
| `claude/add-evolve-to-gamma-Kh22K` | Feature | AlphaEvolve evolution engine | +1,747 | **HIGH** |
| `copilot/add-ollama-backend-adapter` | Feature | Local LLM via Ollama | ~200 | **HIGH** |
| `claude/cli-zed-integration-mRF07` | Feature | Editor integration (Zed, VSCode) | +116 | **MEDIUM** |
| `claude/create-app-flowcharts-oAhVJ` | Docs | Architecture documentation | +docs | **MEDIUM** |
| `claude/assess-prod-readiness-Kh22K` | Docs | Production readiness assessment | +docs | **LOW** |
| `beta` | Enhancement | Testing/security improvements | varies | **LOW** |

---

## Proposed Upgrades (Priority Order)

### 1. MCP Production Wiring [HIGH PRIORITY]
**Branch:** `claude/wire-mcp-production-mRF07`
**Status:** Already implemented, ready to merge

**What it adds:**
- `BacktestTool` class that wraps QuantConnect MCP for real backtesting
- Updated `ValidateCodeTool` with QuantConnect compilation
- CLI commands: `quantcoder validate <file>` and `quantcoder backtest <file>`
- Chat interface integration for `backtest` and `validate` commands
- Config methods: `load_quantconnect_credentials()` and `has_quantconnect_credentials()`
- Fixed `autonomous/pipeline.py` to use real MCP instead of mock data

**Files modified:**
```
quantcoder/tools/code_tools.py    (+195 lines) - Added BacktestTool
quantcoder/config.py              (+33 lines)  - Credential management
quantcoder/cli.py                 (+89 lines)  - CLI commands
quantcoder/chat.py                (+94 lines)  - Chat integration
quantcoder/autonomous/pipeline.py (+64 lines)  - Real MCP calls
quantcoder/tools/__init__.py      (+3 lines)   - Export BacktestTool
```

**Impact:** CRITICAL - Enables actual strategy validation and backtesting

---

### 2. AlphaEvolve Evolution Engine [HIGH PRIORITY]
**Branch:** `claude/add-evolve-to-gamma-Kh22K`
**Status:** Implemented, needs integration review

**What it adds:**
- Complete evolution engine for strategy optimization
- Variation generator for creating strategy mutations
- QC evaluator for ranking variants by Sharpe ratio
- Persistence layer for evolution state and checkpoints
- CLI integration for evolution commands

**New module structure:**
```
quantcoder/evolver/
├── __init__.py      (32 lines)   - Module exports
├── config.py        (99 lines)   - Evolution configuration
├── engine.py        (346 lines)  - Main orchestrator
├── evaluator.py     (319 lines)  - QuantConnect evaluator
├── persistence.py   (272 lines)  - State persistence
└── variation.py     (350 lines)  - Variation generator
```

**Key features:**
- Generate variations from baseline strategy
- Evaluate variants via QuantConnect backtest
- Maintain elite pool of best performers
- Support resumable evolution runs
- Async architecture compatible with gamma

**New CLI commands (proposed):**
```bash
quantcoder evolve start --baseline <file> --generations 50
quantcoder evolve status
quantcoder evolve resume
quantcoder evolve export --format json
```

**Impact:** HIGH - Adds powerful strategy optimization via genetic evolution

---

### 3. Ollama Provider (Local LLM) [HIGH PRIORITY]
**Branch:** `copilot/add-ollama-backend-adapter`
**Status:** Implemented for quantcli, needs port to quantcoder

**What it adds:**
- OllamaAdapter class for local LLM inference
- Support for any Ollama-compatible model (llama2, codellama, mistral, etc.)
- Environment configuration via OLLAMA_BASE_URL and OLLAMA_MODEL
- Chat completion API compatible with existing provider interface

**Required work:**
1. Port OllamaAdapter to quantcoder/llm/providers.py
2. Add "ollama" as provider option in ModelConfig
3. Update config.py to support Ollama settings
4. Add CLI flag: `--provider ollama`

**Proposed implementation:**
```python
# In quantcoder/llm/providers.py

class OllamaProvider(BaseLLMProvider):
    """Provider for local LLM via Ollama."""

    def __init__(self, config):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', config.model.model or 'codellama')

    async def generate(self, prompt: str, **kwargs) -> str:
        # Implementation from copilot branch adapter
        ...
```

**Impact:** HIGH - Enables fully offline/local strategy generation with no API costs

---

### 4. Editor Integration [MEDIUM PRIORITY]
**Branch:** `claude/cli-zed-integration-mRF07`
**Status:** Implemented for quantcli, needs port to quantcoder

**What it adds:**
- `open_in_zed()` function for Zed editor
- `open_in_editor()` generic function supporting:
  - Zed
  - VS Code
  - Cursor
  - Sublime Text
- CLI flags: `--zed`, `--editor <name>`, `--json-output`
- New command: `quantcoder open-code <article_id>`

**Proposed integration:**
```python
# In quantcoder/tools/file_tools.py

def open_in_editor(file_path: str, editor: str = "zed") -> bool:
    """Open file in specified editor."""
    editors = {
        "zed": ["zed", file_path],
        "code": ["code", file_path],
        "cursor": ["cursor", file_path],
        "sublime": ["subl", file_path],
    }
    ...
```

**Impact:** MEDIUM - Improves developer workflow

---

### 5. Architecture Documentation [MEDIUM PRIORITY]
**Branch:** `claude/create-app-flowcharts-oAhVJ`
**Status:** Complete, ready to merge

**What it adds:**
- ARCHITECTURE.md with comprehensive flowcharts
- System architecture diagrams (ASCII art)
- Component relationship documentation
- CHANGELOG.md
- PRODUCTION_SETUP.md
- VERSIONS.md

**Files to merge:**
```
ARCHITECTURE.md
CHANGELOG.md
PRODUCTION_SETUP.md
VERSIONS.md
```

**Impact:** MEDIUM - Essential for onboarding and maintenance

---

### 6. Testing Improvements [LOW PRIORITY]
**Source:** `beta` branch + production readiness assessment

**Recommended additions:**
- Unit tests for agents (coordinator, universe, alpha, risk)
- Integration tests for autonomous pipeline
- Tests for library builder
- Tests for chat interface
- Test coverage reporting

**Current test gap:**
```
COVERED:          NOT COVERED:
- test_llm.py     - agents/*
- test_processor  - autonomous/*
- conftest.py     - library/*
                  - chat.py
                  - cli.py
```

**Impact:** LOW immediate, HIGH long-term for maintainability

---

## Implementation Roadmap

### Phase 1: Production Critical (Immediate)
1. **Merge MCP wiring** from `claude/wire-mcp-production-mRF07`
   - All backtest/validate functionality now works
   - Autonomous mode uses real data

### Phase 2: Feature Enhancement (Week 1)
2. **Port Ollama provider** from `copilot/add-ollama-backend-adapter`
   - Add to providers.py
   - Update config.py
   - Test with codellama

3. **Merge Evolution engine** from `claude/add-evolve-to-gamma-Kh22K`
   - Review integration points
   - Add CLI commands
   - Update documentation

### Phase 3: Developer Experience (Week 2)
4. **Port editor integration** from `claude/cli-zed-integration-mRF07`
   - Add to file_tools.py
   - Update CLI

5. **Merge documentation** from `claude/create-app-flowcharts-oAhVJ`
   - Architecture docs
   - Changelog

### Phase 4: Quality (Ongoing)
6. **Add test coverage**
   - Agent tests
   - Integration tests
   - CI coverage reporting

---

## New Command Reference (After Upgrades)

### Current gamma commands:
```bash
quantcoder chat                    # Interactive chat
quantcoder search <query>          # Search articles
quantcoder download <id>           # Download article
quantcoder summarize <id>          # Summarize article
quantcoder generate <id>           # Generate code
quantcoder auto start              # Autonomous mode
quantcoder library build           # Library builder
```

### Proposed new commands:
```bash
# From MCP wiring (Phase 1)
quantcoder validate <file>         # Validate code on QuantConnect
quantcoder backtest <file>         # Run backtest on QuantConnect

# From Evolution engine (Phase 2)
quantcoder evolve start            # Start evolution
quantcoder evolve status           # Check evolution status
quantcoder evolve resume           # Resume evolution
quantcoder evolve export           # Export elite pool

# From Editor integration (Phase 3)
quantcoder open-code <id>          # Open in editor
quantcoder generate <id> --zed     # Generate and open in Zed
quantcoder generate <id> --editor code  # Generate and open in VS Code
```

### Proposed new config options:
```toml
# ~/.quantcoder/config.toml

[model]
provider = "ollama"        # NEW: "anthropic", "mistral", "deepseek", "openai", "ollama"
ollama_model = "codellama" # NEW: for ollama provider
ollama_url = "http://localhost:11434"  # NEW: custom Ollama server

[ui]
default_editor = "zed"     # NEW: "zed", "code", "cursor", "sublime"
auto_open = true           # NEW: auto-open generated code

[evolution]                # NEW section
max_generations = 50
population_size = 10
elite_size = 3
auto_save = true
```

---

## Risk Assessment

| Upgrade | Risk Level | Mitigation |
|---------|------------|------------|
| MCP wiring | LOW | Already tested, minimal changes |
| Evolution engine | MEDIUM | Large codebase, needs integration review |
| Ollama provider | LOW | Simple adapter pattern |
| Editor integration | LOW | Optional feature, fallback to manual |
| Documentation | NONE | Non-code changes |

---

## Estimated Effort

| Upgrade | Effort | Type |
|---------|--------|------|
| MCP wiring merge | 30 min | Git merge + test |
| Ollama provider port | 2-3 hours | Code adaptation |
| Evolution engine merge | 1-2 hours | Integration review |
| Editor integration port | 1 hour | Code adaptation |
| Documentation merge | 30 min | Git merge |
| **Total** | **5-7 hours** | |

---

## Conclusion

The gamma branch is already 88% production-ready. These upgrades would:

1. **Enable real backtesting** (MCP wiring) - Currently critical gap
2. **Add strategy optimization** (Evolution engine) - Competitive advantage
3. **Support local LLMs** (Ollama) - Cost savings, privacy
4. **Improve DX** (Editor integration) - Workflow improvement
5. **Document architecture** (Docs) - Maintainability

Recommended immediate action: **Merge MCP wiring first** as it's the most critical production gap.

---

## Appendix: Branch Details

### Active Feature Branches
- `gamma` - Main development (v2.0.0-alpha.1)
- `beta` - Improved legacy (v1.1.0-beta.1)
- `main` - Stable production (v1.0.0)
- `claude/wire-mcp-production-mRF07` - MCP wiring
- `claude/add-evolve-to-gamma-Kh22K` - Evolution engine
- `copilot/add-ollama-backend-adapter` - Ollama support

### Documentation Branches
- `claude/create-app-flowcharts-oAhVJ` - Architecture diagrams
- `claude/assess-prod-readiness-Kh22K` - Readiness assessment
- `claude/create-architecture-diagram-mjQqa` - Diagrams + evolver

### Analysis Branches (Read-only reference)
- `claude/compare-agent-architectures-Qc6Ok`
- `claude/compare-gamma-opencode-arch-C4KzZ`
- `claude/audit-gamma-branch-ADxNt`
- `claude/check-credential-leaks-t3ZYa`
