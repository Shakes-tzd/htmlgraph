#!/bin/bash
# Install git hooks for HtmlGraph development
#
# Usage:
#   ./scripts/install-hooks.sh
#
# This script copies hooks from scripts/hooks/ to .git/hooks/
# Run after cloning the repository to enable pre-commit checks.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_SOURCE="$SCRIPT_DIR/hooks"
HOOKS_TARGET="$REPO_ROOT/.git/hooks"

echo "🔧 Installing git hooks..."

# Check we're in a git repo
if [[ ! -d "$REPO_ROOT/.git" ]]; then
    echo "❌ Error: Not a git repository. Run from repository root."
    exit 1
fi

# Check hooks source exists
if [[ ! -d "$HOOKS_SOURCE" ]]; then
    echo "❌ Error: Hooks source directory not found: $HOOKS_SOURCE"
    exit 1
fi

# Install each hook
for hook in "$HOOKS_SOURCE"/*; do
    if [[ -f "$hook" ]]; then
        hook_name=$(basename "$hook")
        target="$HOOKS_TARGET/$hook_name"

        # Backup existing hook if it exists and is different
        if [[ -f "$target" ]]; then
            if ! diff -q "$hook" "$target" > /dev/null 2>&1; then
                echo "  → Backing up existing $hook_name to $hook_name.backup"
                cp "$target" "$target.backup"
            fi
        fi

        # Copy and make executable
        cp "$hook" "$target"
        chmod +x "$target"
        echo "  ✓ Installed $hook_name"
    fi
done

echo ""
echo "✅ Git hooks installed successfully!"
echo ""
echo "Installed hooks will run automatically:"
echo "  • pre-commit: ruff check, ruff format, mypy"
