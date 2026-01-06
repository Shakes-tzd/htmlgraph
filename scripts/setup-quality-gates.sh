#!/bin/bash
# Setup Quality Gates - Install pre-commit hooks
#
# This script installs and configures pre-commit hooks for HtmlGraph
# Hooks enforce code quality standards on every commit
#
# Usage: ./scripts/setup-quality-gates.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}HtmlGraph Quality Gates Setup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f ".pre-commit-config.yaml" ]; then
    echo -e "${RED}✗ Error: .pre-commit-config.yaml not found${NC}"
    echo "  Run this script from the project root directory"
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing pre-commit framework${NC}"
echo "  Installing from PyPI..."

# Try with uv first, fall back to pip
if command -v uv &> /dev/null; then
    uv pip install pre-commit
    INSTALL_CMD="uv pip install"
else
    pip install pre-commit
    INSTALL_CMD="pip install"
fi

echo -e "${GREEN}✓ Pre-commit framework installed${NC}"
echo ""

echo -e "${YELLOW}Step 2: Installing hooks${NC}"
echo "  Registering git hook scripts..."

if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo -e "${GREEN}✓ Hooks installed successfully${NC}"
else
    echo -e "${RED}✗ Error: pre-commit command not found${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 3: Verifying hook installation${NC}"
echo "  Testing hooks on all files..."
echo ""

# Run pre-commit on all files
if pre-commit run --all-files; then
    echo ""
    echo -e "${GREEN}✓ All quality gates passed!${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Quality Gates Setup Complete${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Your project is now protected by pre-commit hooks!"
    echo ""
    echo "Hooks will automatically run when you commit:"
    echo "  • Ruff formatting (auto-fixes code style)"
    echo "  • Ruff linting (auto-fixes code quality issues)"
    echo "  • Mypy (type checking - requires manual fixes)"
    echo "  • Pytest (test validation - requires manual fixes)"
    echo "  • Standard checks (whitespace, file size, etc.)"
    echo ""
    echo "For more information: docs/QUALITY_GATES.md"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠ Some hooks need manual fixes${NC}"
    echo ""
    echo "This is normal on first run. Fix the issues:"
    echo ""
    echo "1. Formatting issues - usually auto-fixed, try again"
    echo "2. Type errors - check docs/QUALITY_GATES.md for guidance"
    echo "3. Test failures - run: uv run pytest"
    echo ""
    echo "Then install hooks again:"
    echo "  pre-commit install"
    echo ""
    exit 1
fi
