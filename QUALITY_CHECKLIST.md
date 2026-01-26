# QuantCoder CLI - Quick Quality Improvement Checklist

**Version:** v2.0.0  
**Last Updated:** January 26, 2026

This checklist provides a quick reference for improving repository quality. For detailed analysis, see [QUALITY_ASSESSMENT.md](QUALITY_ASSESSMENT.md).

---

## 🔴 Critical Issues (Fix Immediately)

- [ ] **Format code with Black**
  ```bash
  black .
  ```
  - Files affected: 30
  - Time: ~5 minutes
  - Blocks: CI pipeline

- [ ] **Fix auto-correctable linting errors**
  ```bash
  ruff check . --fix
  ```
  - Errors: 393/459 auto-fixable
  - Time: ~5 minutes
  - Blocks: CI pipeline

- [ ] **Add missing test dependency**
  Edit `pyproject.toml`:
  ```toml
  [project.optional-dependencies]
  dev = [
      # ... existing dependencies ...
      "pytest-asyncio>=0.21.0",
  ]
  ```
  - Fixes: 38 test failures
  - Time: ~2 minutes

- [ ] **Resolve license inconsistency**
  - Issue: `pyproject.toml` says MIT, `LICENSE` file says Apache 2.0
  - Action: Choose one and update accordingly
  - Time: ~5 minutes

---

## 🟡 High Priority (Fix This Week)

- [ ] **Fix remaining linting errors manually**
  ```bash
  ruff check .
  ```
  - Remaining: ~66 issues
  - Time: ~2 hours
  - Issues include: imports, type hints, security warnings

- [ ] **Fix ValidateCodeTool interface**
  - Location: `quantcoder/tools/*.py`
  - Issue: Unexpected `file_path` argument in tests
  - Fixes: 7 test failures
  - Time: ~30 minutes

- [ ] **Address security warnings**
  - [ ] S105: Hardcoded password string (1 instance)
  - [ ] S324: Insecure hash function (1 instance)
  - [ ] S314: XML parsing security (1 instance)
  - Time: ~1-2 hours

- [ ] **Clean up repository artifacts**
  ```bash
  rm -rf MagicMock/
  ```
  - Time: ~2 minutes

- [ ] **Configure pre-commit hooks**
  ```bash
  pre-commit install
  ```
  - Time: ~15 minutes
  - Prevents future issues

---

## 🟢 Medium Priority (Next Sprint)

- [ ] **Mock external API calls in tests**
  - File: `tests/test_tools.py`
  - Fixes: SearchArticlesTool test failures
  - Time: ~1 hour

- [ ] **Improve code documentation**
  - [ ] Add docstrings to modules without them
  - [ ] Target: All public APIs documented
  - [ ] Consider: Sphinx for API docs
  - Time: ~4 hours

- [ ] **Update README**
  - [ ] Remove "not systematically tested" warning (once tests pass)
  - [ ] Add CI status badge
  - [ ] Add code coverage badge
  - Time: ~15 minutes

- [ ] **Increase test coverage**
  - Current: ~80% tests passing
  - Target: >85% coverage, >95% passing
  - Time: ~4-8 hours

---

## ⚪ Low Priority (Nice to Have)

- [ ] **Create CONTRIBUTING.md**
  - Guidelines for contributors
  - Code style requirements
  - PR process
  - Time: ~1 hour

- [ ] **Create SECURITY.md**
  - Security policy
  - Vulnerability reporting
  - Time: ~30 minutes

- [ ] **Add GitHub Issue Templates**
  - Bug report template
  - Feature request template
  - Time: ~30 minutes

- [ ] **Add Pull Request Template**
  - Checklist for PRs
  - Testing requirements
  - Time: ~15 minutes

- [ ] **Set up Dependabot**
  - Automatic dependency updates
  - Security alerts
  - Time: ~15 minutes

---

## Quality Metrics Target

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Test Pass Rate | 80.3% | 95%+ | 🟡 Needs work |
| Code Coverage | Unknown | 85%+ | 🟡 Measure first |
| Linting Errors | 459 | 0 | 🔴 Critical |
| Formatting Issues | 30 files | 0 | 🔴 Critical |
| Security Issues | 3 | 0 | 🟡 High priority |
| Documentation | Excellent | Maintain | 🟢 Good |
| CI Pipeline | Failing | Passing | 🔴 Critical |

---

## Quick Commands Reference

### Run all quality checks locally:

```bash
# Format code
black .

# Fix auto-correctable linting
ruff check . --fix

# Check remaining linting issues
ruff check .

# Type check
mypy quantcoder --ignore-missing-imports

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=quantcoder --cov-report=html

# Security audit
pip-audit

# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

---

## Progress Tracking

**Last Updated:** January 26, 2026  
**Completed:** 0/4 Critical, 0/5 High Priority, 0/4 Medium Priority  
**Overall Progress:** 0/13 (0%)

Update this section as you complete items!

---

## Notes

- Focus on critical issues first - they block the CI pipeline
- High priority issues affect functionality and security
- Medium/low priority items improve long-term maintainability
- Run quality checks before each commit to catch issues early

**Estimated Time to Complete All Critical + High Priority Items:** 4-6 hours

