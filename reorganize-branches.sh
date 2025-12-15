#!/bin/bash
# QuantCoder Branch Reorganization Script
# This script creates clean branch names: main, beta, gamma

set -e

echo "🔄 QuantCoder Branch Reorganization"
echo "===================================="
echo ""

# Check if we're in the right repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo "📍 Current branches:"
git branch -r
echo ""

# Ask for confirmation
read -p "This will create new branches (main, beta, gamma). Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Step 1: Fetch all branches..."
git fetch --all

echo ""
echo "Step 2: Create beta branch from refactor/modernize-2025..."
git checkout refactor/modernize-2025 2>/dev/null || git checkout -b beta origin/refactor/modernize-2025
git checkout -b beta-clean
git push origin beta-clean:beta
echo "✓ Beta branch created"

echo ""
echo "Step 3: Create gamma branch from current work..."
git checkout claude/refactor-quantcoder-cli-JwrsM 2>/dev/null || git checkout -b gamma origin/claude/refactor-quantcoder-cli-JwrsM
git checkout -b gamma-clean
git push origin gamma-clean:gamma
echo "✓ Gamma branch created"

echo ""
echo "Step 4: Verify main branch exists..."
git checkout main
echo "✓ Main branch ready"

echo ""
echo "✅ Branch reorganization complete!"
echo ""
echo "New branches:"
echo "  • main  (v1.0.0)          - Stable"
echo "  • beta  (v1.1.0-beta.1)   - Testing"
echo "  • gamma (v2.0.0-alpha.1)  - Latest"
echo ""
echo "Next steps:"
echo "1. Verify the new branches on GitHub"
echo "2. Update your local git config if needed"
echo "3. Optionally delete old branches:"
echo "   git push origin --delete claude/refactor-quantcoder-cli-JwrsM"
echo "   git push origin --delete refactor/modernize-2025"
echo ""
