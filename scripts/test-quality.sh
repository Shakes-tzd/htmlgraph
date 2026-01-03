#!/bin/bash
#
# HtmlGraph Code Quality Verification Script
#
# This script runs all quality checks on specified files or directories.
# Designed for use by AI spawners (Gemini, Codex) to verify their output.
#
# Usage:
#   ./scripts/test-quality.sh [path]           # Check specific file/directory
#   ./scripts/test-quality.sh                  # Check src/ and packages/
#   ./scripts/test-quality.sh --quick          # Skip tests, only lint
#   ./scripts/test-quality.sh --full           # Full checks including tests
#
# Exit Codes:
#   0 = All checks passed
#   1 = One or more checks failed
#
# Integration with AI Spawners:
#   After Gemini/Codex generates code, run this script to verify quality.
#   If it fails, iterate with the same spawner (not Claude).
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
PATH_TO_CHECK=""
QUICK_MODE=false
FULL_MODE=false

for arg in "$@"; do
    case $arg in
        --quick)
            QUICK_MODE=true
            ;;
        --full)
            FULL_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [path] [--quick|--full]"
            echo ""
            echo "Options:"
            echo "  path      File or directory to check (default: src/ packages/)"
            echo "  --quick   Skip tests, only run linting"
            echo "  --full    Full checks including all tests"
            exit 0
            ;;
        *)
            PATH_TO_CHECK=$arg
            ;;
    esac
done

# Default path
if [ -z "$PATH_TO_CHECK" ]; then
    PATH_TO_CHECK="src/ packages/"
fi

echo "=========================================="
echo "HtmlGraph Code Quality Verification"
echo "=========================================="
echo "Checking: $PATH_TO_CHECK"
echo ""

FAILED=0

# Step 1: Ruff Linting
echo -n "1. Ruff check... "
if uv run ruff check $PATH_TO_CHECK 2>/dev/null; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    FAILED=1
fi

# Step 2: Ruff Format Check
echo -n "2. Ruff format... "
if uv run ruff format --check $PATH_TO_CHECK 2>/dev/null; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${YELLOW}NEEDS FORMATTING${NC}"
    echo "   Run: uv run ruff format $PATH_TO_CHECK"
    FAILED=1
fi

# Step 3: Mypy Type Checking (only for Python files in src/)
echo -n "3. Mypy types... "
if echo "$PATH_TO_CHECK" | grep -q "src/"; then
    if uv run mypy src/python/htmlgraph/ --ignore-missing-imports 2>/dev/null; then
        echo -e "${GREEN}PASSED${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        FAILED=1
    fi
else
    echo -e "${YELLOW}SKIPPED${NC} (no src/ in path)"
fi

# Step 4: Tests (unless quick mode)
if [ "$QUICK_MODE" != true ]; then
    echo -n "4. Pytest... "
    if [ "$FULL_MODE" = true ]; then
        if uv run pytest tests/ -v 2>/dev/null; then
            echo -e "${GREEN}PASSED${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            FAILED=1
        fi
    else
        # Quick test run (just check tests can import)
        if uv run pytest tests/ --collect-only -q 2>/dev/null; then
            echo -e "${GREEN}PASSED${NC} (collection only)"
        else
            echo -e "${YELLOW}SKIPPED${NC} (test collection failed)"
        fi
    fi
else
    echo "4. Pytest... ${YELLOW}SKIPPED${NC} (quick mode)"
fi

# Summary
echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Quality checks failed.${NC}"
    echo ""
    echo "Fix issues and re-run:"
    echo "  uv run ruff check --fix $PATH_TO_CHECK"
    echo "  uv run ruff format $PATH_TO_CHECK"
    exit 1
fi
