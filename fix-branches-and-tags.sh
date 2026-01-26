#!/bin/bash
# Branch and Tag Cleanup Script
# This script will:
# 1. Reset main to the restored beta content (with stability warning)
# 2. Merge the v2.0.0 update into gamma (with testing warning)
# 3. Create proper version tags (v1.0.0, v1.1.0, v2.0.0)
# 4. Delete deprecated v0.x tags

set -e  # Exit on error

echo "=============================================="
echo "QuantCoder Branch & Tag Cleanup"
echo "=============================================="
echo ""

# Step 1: Reset main branch
echo "[1/4] Resetting main branch to restored beta content..."
git fetch origin
git checkout main
git reset --hard origin/claude/restore-main-v1.0.0-fR2Y1
git push --force origin main
echo "✓ Main branch reset complete"
echo ""

# Step 2: Update gamma branch
echo "[2/4] Updating gamma branch with v2.0.0 changes..."
git checkout gamma
git merge origin/claude/update-gamma-v2.0.0-fR2Y1 -m "Update to v2.0.0 and add testing warning"
git push origin gamma
echo "✓ Gamma branch updated"
echo ""

# Step 3: Create new tags
echo "[3/4] Creating version tags..."
git tag -d v1.0.0 2>/dev/null || true
git tag -d v1.1.0 2>/dev/null || true
git tag -d v2.0.0 2>/dev/null || true

git tag v1.0.0 main -m "v1.0.0 - Legacy stable (restored from beta)"
git tag v1.1.0 origin/beta -m "v1.1.0 - Legacy development branch"
git tag v2.0.0 gamma -m "v2.0.0 - New architecture (complete rewrite)"

git push origin v1.0.0 v1.1.0 v2.0.0 --force
echo "✓ Tags created: v1.0.0, v1.1.0, v2.0.0"
echo ""

# Step 4: Delete old tags
echo "[4/4] Deleting deprecated v0.x tags..."
git tag -d v0.1 v0.2 v0.3 2>/dev/null || true
git push origin --delete v0.1 v0.2 v0.3 2>/dev/null || echo "Some remote tags may already be deleted"
echo "✓ Old tags deleted"
echo ""

echo "=============================================="
echo "COMPLETE! New structure:"
echo "=============================================="
echo ""
echo "Branches:"
echo "  main  -> v1.0.0 (legacy stable, quantcli)"
echo "  beta  -> v1.1.0 (legacy dev, quantcli)"
echo "  gamma -> v2.0.0 (new architecture, quantcoder)"
echo ""
echo "Tags:"
echo "  v1.0.0 -> main"
echo "  v1.1.0 -> beta"
echo "  v2.0.0 -> gamma"
echo ""
echo "Old tags v0.1, v0.2, v0.3 have been removed."
