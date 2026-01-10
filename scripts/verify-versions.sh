#!/bin/bash
#
# HtmlGraph Version Synchronization Verification Script
#
# Verifies that all version files are synchronized:
# - pyproject.toml
# - src/python/htmlgraph/__init__.py
# - packages/claude-plugin/.claude-plugin/plugin.json
# - packages/gemini-extension/gemini-extension.json
#
# Also verifies hook shebangs reference the correct version
#
# Usage:
#   ./scripts/verify-versions.sh              # Check current versions
#   ./scripts/verify-versions.sh 0.25.0       # Verify target version
#   ./scripts/verify-versions.sh --check      # Show current versions
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Version files to check
PYPROJECT_TOML="$PROJECT_ROOT/pyproject.toml"
INIT_PY="$PROJECT_ROOT/src/python/htmlgraph/__init__.py"
PLUGIN_JSON="$PROJECT_ROOT/packages/claude-plugin/.claude-plugin/plugin.json"
GEMINI_JSON="$PROJECT_ROOT/packages/gemini-extension/gemini-extension.json"

# Hook scripts that need version verification
HOOK_SCRIPTS=(
    "$PROJECT_ROOT/packages/claude-plugin/.claude-plugin/hooks/scripts/session-start.py"
    "$PROJECT_ROOT/packages/claude-plugin/.claude-plugin/hooks/scripts/user-prompt-submit.py"
    "$PROJECT_ROOT/packages/claude-plugin/.claude-plugin/hooks/scripts/track-event.py"
)

# Parse arguments
TARGET_VERSION=""
CHECK_ONLY=false

for arg in "$@"; do
    case $arg in
        --check)
            CHECK_ONLY=true
            ;;
        --help|-h)
            echo "Usage: $0 [VERSION] [--check]"
            echo ""
            echo "Arguments:"
            echo "  VERSION         Target version to verify (e.g., 0.25.0)"
            echo "  --check         Show current versions without verification"
            echo ""
            echo "Version files checked:"
            echo "  - pyproject.toml"
            echo "  - src/python/htmlgraph/__init__.py"
            echo "  - packages/claude-plugin/.claude-plugin/plugin.json"
            echo "  - packages/gemini-extension/gemini-extension.json"
            echo ""
            echo "Hook shebangs verified to match version format"
            exit 0
            ;;
        *)
            TARGET_VERSION=$arg
            ;;
    esac
done

# Extract current versions from files
extract_version() {
    local file=$1
    local pattern=$2

    if [ ! -f "$file" ]; then
        echo "NOT_FOUND"
        return
    fi

    # Use sed to extract version number (portable across macOS and Linux)
    sed -n "/$pattern/p" "$file" | head -1 | sed -E 's/.*([0-9]+\.[0-9]+\.[0-9]+).*/\1/' || echo "NOT_FOUND"
}

echo -e "${BLUE}HtmlGraph Version Verification${NC}"
echo ""

# Get versions from all files
PYPROJECT_VER=$(extract_version "$PYPROJECT_TOML" 'version')
INIT_VER=$(extract_version "$INIT_PY" '__version__')
PLUGIN_VER=$(extract_version "$PLUGIN_JSON" '"version"')
GEMINI_VER=$(extract_version "$GEMINI_JSON" '"version"')

echo "Current versions:"
echo "  pyproject.toml:                 $PYPROJECT_VER"
echo "  src/python/htmlgraph/__init__.py: $INIT_VER"
echo "  plugin.json:                    $PLUGIN_VER"
echo "  gemini-extension.json:          $GEMINI_VER"
echo ""

# Check if all versions match
VERSIONS_MATCH=true
if [ "$PYPROJECT_VER" != "$INIT_VER" ] || \
   [ "$PYPROJECT_VER" != "$PLUGIN_VER" ] || \
   [ "$PYPROJECT_VER" != "$GEMINI_VER" ]; then
    VERSIONS_MATCH=false
fi

if [ "$CHECK_ONLY" = true ]; then
    if [ "$VERSIONS_MATCH" = true ]; then
        echo -e "${GREEN}✓ All versions match${NC}"
        exit 0
    else
        echo -e "${RED}✗ Versions are out of sync${NC}"
        exit 1
    fi
fi

# If target version specified, verify all files match it
if [ -n "$TARGET_VERSION" ]; then
    echo "Verifying target version: $TARGET_VERSION"
    echo ""

    ERRORS=0

    # Check each file
    if [ "$PYPROJECT_VER" != "$TARGET_VERSION" ]; then
        echo -e "${RED}✗ pyproject.toml: $PYPROJECT_VER (expected $TARGET_VERSION)${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ pyproject.toml: $PYPROJECT_VER${NC}"
    fi

    if [ "$INIT_VER" != "$TARGET_VERSION" ]; then
        echo -e "${RED}✗ src/python/htmlgraph/__init__.py: $INIT_VER (expected $TARGET_VERSION)${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ src/python/htmlgraph/__init__.py: $INIT_VER${NC}"
    fi

    if [ "$PLUGIN_VER" != "$TARGET_VERSION" ]; then
        echo -e "${RED}✗ plugin.json: $PLUGIN_VER (expected $TARGET_VERSION)${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ plugin.json: $PLUGIN_VER${NC}"
    fi

    if [ "$GEMINI_VER" != "$TARGET_VERSION" ]; then
        echo -e "${RED}✗ gemini-extension.json: $GEMINI_VER (expected $TARGET_VERSION)${NC}"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓ gemini-extension.json: $GEMINI_VER${NC}"
    fi

    echo ""

    # Check hook shebangs
    echo "Checking hook shebangs..."
    HOOK_ERRORS=0
    for script in "${HOOK_SCRIPTS[@]}"; do
        if [ -f "$script" ]; then
            shebang=$(head -1 "$script")
            expected_version="htmlgraph>=$TARGET_VERSION"

            if echo "$shebang" | grep -F "$expected_version" > /dev/null; then
                echo -e "${GREEN}✓ $(basename "$script")${NC}"
            else
                echo -e "${RED}✗ $(basename "$script"): shebang doesn't match version${NC}"
                echo "  Expected: --with $expected_version"
                echo "  Found: $shebang"
                HOOK_ERRORS=$((HOOK_ERRORS + 1))
            fi
        fi
    done

    ERRORS=$((ERRORS + HOOK_ERRORS))
    echo ""

    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ All versions and shebangs are synchronized${NC}"
        exit 0
    else
        echo -e "${RED}✗ Found $ERRORS error(s)${NC}"
        echo ""
        echo "To fix version numbers, update:"
        echo "  1. pyproject.toml: version = \"$TARGET_VERSION\""
        echo "  2. src/python/htmlgraph/__init__.py: __version__ = \"$TARGET_VERSION\""
        echo "  3. packages/claude-plugin/.claude-plugin/plugin.json: \"version\": \"$TARGET_VERSION\""
        echo "  4. packages/gemini-extension/gemini-extension.json: \"version\": \"$TARGET_VERSION\""
        echo ""
        echo "To fix hook shebangs, update to:"
        echo "  #!/usr/bin/env -S uv run --with htmlgraph>=$TARGET_VERSION"
        exit 1
    fi
else
    # No target version specified, just check if all current versions match
    echo ""
    if [ "$VERSIONS_MATCH" = true ]; then
        echo -e "${GREEN}✓ All versions match (current: $PYPROJECT_VER)${NC}"
        exit 0
    else
        echo -e "${RED}✗ Versions are out of sync${NC}"
        echo ""
        echo "To fix, update all files to the same version and run:"
        echo "  ./scripts/verify-versions.sh TARGET_VERSION"
        exit 1
    fi
fi
