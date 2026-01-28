# Branch Assessment Report

**Assessment Date:** 2026-01-28
**Repository:** quantcoder-cli
**Assessed Branches:** main, gamma, beta, last-stable-version

---

## Executive Summary

| Branch | Version | Status | Production Ready | Recommendation |
|--------|---------|--------|------------------|----------------|
| **gamma** | 2.0.0 | Active | **Yes** | **Best for Production** |
| main | 2.0.0 | Active | No (untested) | Best for Latest Features |
| beta | 1.1.0 | Legacy | Stable | Legacy maintenance only |
| last-stable-version | 1.0.0 | Archived | Yes | Historical reference |

### Recommendation: **gamma** is the best version for production use

---

## Detailed Branch Analysis

### 1. gamma (Recommended)

**Version:** 2.0.0
**Last Commit:** `16b166d` - Merge production readiness review
**Source Lines:** 10,362 (lean, focused codebase)
**Test Files:** 15

**Strengths:**
- **Production Readiness Review completed** - Passed with "Yes - Production Ready" verdict
- **Fully async network calls** - All HTTP operations use `aiohttp` (non-blocking)
- **Docker support** - Multi-stage Dockerfile, docker-compose, non-root user
- **Security hardened** - 7/8 CVEs fixed, keyring credential storage, path traversal protection
- **Comprehensive testing** - 229+ tests, E2E tests, CLI tests, performance benchmarks
- **Operational documentation** - Runbook, troubleshooting guide, CODEOWNERS
- **Circuit breaker pattern** - Resilient external API handling
- **Parallel evaluation** - 3-5x speedup in evolution engine

**Unique Files:**
- `Dockerfile` + `docker-compose.yml`
- `PRODUCTION_READINESS_REVIEW.md`
- `docs/RUNBOOK.md` + `docs/TROUBLESHOOTING.md`
- `tests/test_cli.py`, `tests/test_e2e.py`, `tests/test_performance.py`
- `.env.example`, `.github/CODEOWNERS`

**Missing vs main:**
- No scheduler/automated pipeline
- No Tavily deep search integration
- No Notion client integration

---

### 2. main (Current HEAD)

**Version:** 2.0.0
**Last Commit:** `d813f94` - Merge automated backtest workflow
**Source Lines:** 13,738 (feature-rich)
**Test Files:** 17

**Strengths:**
- **Most features** - Scheduler, automated pipeline, Notion integration
- **Tavily deep search** - Semantic paper discovery
- **Multi-article workflow** - Consolidated summaries
- **Centralized logging** - Process monitoring
- **HTTP utilities** - Retry/caching layer

**Weaknesses:**
- **README warning:** "has not been systematically tested yet"
- **Synchronous HTTP in places** - Uses blocking `requests` in some tools
- **No Docker support** - Missing containerization
- **No production review** - Untested for production deployment

**Unique Files:**
- `quantcoder/scheduler/` - Automated pipeline, Notion client
- `quantcoder/tools/deep_search.py` - Tavily integration
- `quantcoder/logging_config.py`, `quantcoder/core/http_utils.py`
- `docs/QUANTCODER_GUIDE.md`

---

### 3. beta (Legacy)

**Version:** 1.1.0
**License:** MIT (vs Apache 2.0 in v2.x)
**Status:** Legacy development version

**Characteristics:**
- Simpler architecture (dual-agent vs multi-agent)
- OpenAI SDK 1.x support
- Python 3.9+ (vs 3.10+ in v2.x)
- Good for users who need v1.x compatibility

---

### 4. last-stable-version (Archived)

**Version:** 1.0.0
**Status:** Original stable release, archived

**Use Case:** Historical reference or rollback point for v1.x users

---

## Feature Comparison Matrix

| Feature | main | gamma | beta |
|---------|------|-------|------|
| Multi-agent system | ✅ | ✅ | ❌ |
| AlphaEvolve evolution | ✅ | ✅ | ❌ |
| Async HTTP (aiohttp) | ❌ | ✅ | ❌ |
| Docker support | ❌ | ✅ | ❌ |
| Production review | ❌ | ✅ | ❌ |
| Automated scheduler | ✅ | ❌ | ❌ |
| Tavily deep search | ✅ | ❌ | ❌ |
| Notion integration | ✅ | ❌ | ❌ |
| E2E tests | ❌ | ✅ | ❌ |
| Performance tests | ❌ | ✅ | ❌ |
| CLI tests | ❌ | ✅ | ❌ |
| Circuit breaker | ❌ | ✅ | ❌ |
| Security CVE fixes | Partial | ✅ | ❌ |

---

## Divergence Analysis

**Common Ancestor:** `e18607b` (Merge update-gamma-v2.0.0)

```
main ─────────────────► d813f94 (62 commits ahead)
              │
              ├─ Adds: scheduler, deep search, Notion
              ├─ Keeps: synchronous requests in places
              └─ Warning: "not systematically tested"

gamma ────────────────► 16b166d (production-ready)
              │
              ├─ Adds: Docker, async, production hardening
              ├─ Removes: scheduler, deep search features
              └─ Status: Production Ready
```

**Files only in main:** 17 (scheduler, deep search, logging)
**Files only in gamma:** 10 (Docker, production docs, E2E tests)

---

## Recommendations

### For Production Deployment
**Use `gamma`** - It has passed production readiness review with comprehensive testing, Docker support, and security hardening.

### For Development/Testing New Features
**Use `main`** - It has the latest features including scheduler, deep search, and Notion integration, but requires more testing.

### For Legacy Compatibility
**Use `beta` or `last-stable-version`** - If you need v1.x architecture or MIT license.

### Optimal Strategy
**Merge main's unique features INTO gamma** to create the best of both worlds:
1. Cherry-pick scheduler/automated_pipeline from main
2. Cherry-pick deep_search tool from main
3. Cherry-pick Notion client from main
4. Apply gamma's async patterns to new code
5. Add tests for new features

This would yield a production-ready branch with all features.

---

## Version Tags

| Tag | Commit | Branch | Notes |
|-----|--------|--------|-------|
| v2.0.0 | `5abba09` | gamma/main | Current major version |
| v1.1.0 | beta | beta | Legacy with improvements |
| v1.0.0 | last-stable-version | archived | Original stable |

---

*Report generated by automated branch assessment*
