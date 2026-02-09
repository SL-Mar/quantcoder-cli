# QuantCoder CLI - Production Setup Instructions

## Overview

**Goal:** Set up production-ready repository with 2 versions and clean branch structure.

### Target State

```
BRANCHES:                    TAGS:
─────────                    ─────
main     (stable)            v1.0 → main (legacy)
beta     (to be deleted)     v1.1 → beta (enhanced)
develop  (v2.0 WIP)

After cleanup: main + develop only
```

### Version Summary

| Version | Source | Features |
|---------|--------|----------|
| v1.0 | main | Legacy, OpenAI v0.28, Tkinter GUI |
| v1.1 | beta | + LLM client abstraction, + QC static validator |
| v2.0 | develop (from gamma) | Multi-agent, autonomous, library builder |

---

## Step-by-Step Instructions

### Phase 1: Create Tags

```bash
# Tag main as v1.0
git checkout main
git tag -a v1.0 -m "v1.0: Legacy - OpenAI v0.28, Tkinter GUI, basic features"
git push origin v1.0

# Tag beta as v1.1
git checkout beta
git tag -a v1.1 -m "v1.1: LLM client abstraction + QC static validator"
git push origin v1.1
```

### Phase 2: Rename gamma → develop

```bash
git checkout gamma
git checkout -b develop
git push origin develop
git push origin --delete gamma
```

### Phase 3: Merge Documentation

```bash
git checkout main
git merge origin/claude/create-app-flowcharts-oAhVJ -m "Add version documentation"
git push origin main
```

**Files added:**
- `ARCHITECTURE.md` - Gamma branch flowcharts
- `VERSIONS.md` - Version comparison guide
- `CHANGELOG.md` - Detailed changelog

### Phase 4: Delete Old Branches

```bash
# Delete merged/obsolete branches
git push origin --delete beta
git push origin --delete claude/assess-gamma-quality-d5N6F
git push origin --delete claude/audit-gamma-branch-ADxNt
git push origin --delete claude/check-credential-leaks-t3ZYa
git push origin --delete claude/compare-gamma-opencode-arch-C4KzZ
git push origin --delete claude/create-app-flowcharts-oAhVJ
git push origin --delete copilot/add-ollama-backend-adapter
```

### Phase 5: Verify

```bash
# Check branches (should be: main, develop)
git branch -a

# Check tags
git tag -l

# Expected output:
# Branches: main, develop
# Tags: v1.0, v1.1
```

---

## Alternative: GitHub Web Interface

If using mobile/web browser:

### Create Tags (via Releases)
1. Go to **Releases** → **Create a new release**
2. **Choose a tag** → type `v1.0` → **Create new tag**
3. **Target:** select `main`
4. **Title:** `v1.0: Legacy Release`
5. **Publish release**
6. Repeat for `v1.1` targeting `beta`

### Create develop branch
1. Go to **Code** tab
2. Click branch dropdown (shows `main`)
3. Type `develop`
4. Select **Create branch: develop from gamma**

### Delete branches
1. Go to **Branches** (click "X branches")
2. Click 🗑️ trash icon next to each unwanted branch

### Merge documentation PR
1. Go to **Pull requests**
2. Create PR from `claude/create-app-flowcharts-oAhVJ` → `main`
3. Merge

---

## Final Repository Structure

```
quantcoder-cli/
├── main branch (v1.0 code + docs)
│   ├── quantcli/           # v1.0 package
│   ├── ARCHITECTURE.md     # Flowcharts
│   ├── VERSIONS.md         # Version guide
│   ├── CHANGELOG.md        # Changelog
│   └── README.md
│
├── develop branch (v2.0 WIP)
│   ├── quantcoder/         # v2.0 package (new name)
│   ├── agents/
│   ├── autonomous/
│   ├── library/
│   └── ...
│
└── Tags
    ├── v1.0 → points to main (legacy)
    └── v1.1 → points to beta commit (enhanced)
```

---

## Release Workflow

### v2.0.0 Release (Ollama-only, local models)

```bash
# Merge develop into main
git checkout main
git merge develop
git tag -a v2.0.0 -m "v2.0.0: Ollama-only local LLM inference"
git push origin main --tags

# v1.0 and v1.1 remain accessible via tags
git checkout v1.0  # Access old version anytime
```

### Prerequisites for v2.0.0
- Ollama installed and running
- Models pulled: `ollama pull qwen2.5-coder:14b && ollama pull mistral`
- No cloud API keys required

---

## Checklist

- [ ] Tag main as v1.0
- [ ] Tag beta as v1.1
- [ ] Create develop branch from gamma
- [ ] Delete gamma branch
- [ ] Merge docs to main
- [ ] Delete claude/* branches (5)
- [ ] Delete copilot/* branch (1)
- [ ] Delete beta branch
- [ ] Verify: 2 branches + 2 tags

---

## Quick Reference

| Action | Command |
|--------|---------|
| List branches | `git branch -a` |
| List tags | `git tag -l` |
| Checkout version | `git checkout v1.0` |
| Delete remote branch | `git push origin --delete <branch>` |
| Create tag | `git tag -a v1.0 -m "message"` |
| Push tag | `git push origin v1.0` |
