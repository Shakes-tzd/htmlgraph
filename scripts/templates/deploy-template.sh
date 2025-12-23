#!/bin/bash
#
# Deployment Script Template for Python Packages
#
# This is a template for deploying Python packages with flexible deployment options.
# Copy this file to your project's scripts/ directory and customize the CONFIGURATION SECTION.
#
# Features:
# - Flexible deployment modes (--docs-only, --build-only, etc.)
# - Dry-run support for previewing changes
# - PyPI publishing with optional authentication
# - Local installation verification
# - Plugin/extension updates (optional)
# - Colored output for better readability
#
# Usage:
#   ./scripts/deploy.sh [version] [flags]
#
# Examples:
#   ./scripts/deploy.sh 0.5.0              # Full release
#   ./scripts/deploy.sh --docs-only        # Just commit + push
#   ./scripts/deploy.sh 0.5.0 --skip-pypi  # Build but don't publish
#   ./scripts/deploy.sh --dry-run          # Preview actions
#
# Flags:
#   --docs-only     Only commit and push to git (skip build/publish)
#   --build-only    Only build package (skip git/publish/install)
#   --skip-pypi     Skip PyPI publishing step
#   --skip-plugins  Skip plugin/extension update steps
#   --dry-run       Show what would happen without executing
#   --help          Show this help message
#

set -e  # Exit on error

# ============================================================================
# CONFIGURATION SECTION - CUSTOMIZE FOR YOUR PROJECT
# ============================================================================

# Package metadata
PACKAGE_NAME="YOUR_PACKAGE_NAME"
PROJECT_ROOT_FILE="pyproject.toml"
VERSION_PYTHON_FILE="src/python/${PACKAGE_NAME}/__init__.py"

# PyPI configuration
PYPI_PROJECT_URL="https://pypi.org/project/${PACKAGE_NAME}/"
PYPI_PUBLISH_PATTERN="dist/${PACKAGE_NAME}-\${VERSION}*"

# Plugin configurations (set to false to disable)
CLAUDE_PLUGIN_ENABLED=false
GEMINI_EXTENSION_ENABLED=false
CODEX_SKILL_ENABLED=false
GEMINI_EXTENSION_DIR="packages/gemini-extension"
GEMINI_CONFIG_FILE="${GEMINI_EXTENSION_DIR}/gemini-extension.json"

# Build configuration
BUILD_COMMAND="uv build"  # or: python -m build
CLEAN_DIST=true
PUBLISH_COMMAND="uv publish"  # or: twine upload

# Git configuration
GIT_REMOTE="origin"
GIT_BRANCH="main"
PYPI_WAIT_SECONDS=10

# Installation configuration
INSTALL_COMMAND="pip install"
INSTALL_METHOD="--upgrade"  # or "--force-reinstall"

# ============================================================================
# END CONFIGURATION SECTION
# ============================================================================

# Parse flags
DOCS_ONLY=false
BUILD_ONLY=false
SKIP_PYPI=false
SKIP_PLUGINS=false
DRY_RUN=false
VERSION=""

show_help() {
    echo "Deployment Script for $PACKAGE_NAME"
    echo ""
    echo "Usage: $0 [version] [flags]"
    echo ""
    echo "Flags:"
    echo "  --docs-only     Only commit and push to git (skip build/publish)"
    echo "  --build-only    Only build package (skip git/publish/install)"
    echo "  --skip-pypi     Skip PyPI publishing step"
    echo "  --skip-plugins  Skip plugin update steps"
    echo "  --dry-run       Show what would happen without executing"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 0.5.0                    # Full release"
    echo "  $0 --docs-only              # Just commit + push"
    echo "  $0 0.5.0 --skip-pypi        # Build but don't publish"
    echo "  $0 --build-only             # Just build package"
    echo "  $0 --dry-run                # Preview actions"
    exit 0
}

# Parse arguments
for arg in "$@"; do
    case $arg in
        --docs-only)
            DOCS_ONLY=true
            ;;
        --build-only)
            BUILD_ONLY=true
            ;;
        --skip-pypi)
            SKIP_PYPI=true
            ;;
        --skip-plugins)
            SKIP_PLUGINS=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            show_help
            ;;
        *)
            if [[ ! $arg =~ ^-- ]] && [ -z "$VERSION" ]; then
                VERSION=$arg
            fi
            ;;
    esac
done

# Get version from argument or detect from pyproject.toml
if [ -z "$VERSION" ]; then
    VERSION=$(python -c "
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
" 2>/dev/null || echo "unknown")
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    echo -e "ℹ️  $1"
}

# Dry-run wrapper
run_command() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would run: $@"
    else
        "$@"
    fi
}

# Determine what to run
if [ "$DOCS_ONLY" = true ]; then
    log_section "Deployment - DOCS ONLY Mode"
    SKIP_BUILD=true
    SKIP_PYPI=true
    SKIP_INSTALL=true
    SKIP_PLUGINS=true
elif [ "$BUILD_ONLY" = true ]; then
    log_section "Deployment - BUILD ONLY Mode"
    SKIP_GIT=true
    SKIP_PYPI=true
    SKIP_INSTALL=true
    SKIP_PLUGINS=true
else
    log_section "Deployment - Version $VERSION"
    SKIP_GIT=false
    SKIP_BUILD=false
    SKIP_INSTALL=false
fi

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY-RUN MODE - No actual changes will be made"
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    log_error "Must be run from project root (where pyproject.toml is)"
    exit 1
fi

# Load PyPI token from .env if it exists
if [ -f ".env" ]; then
    log_info "Loading environment variables from .env"
    source .env
fi

# ============================================================================
# STEP 1: Git Push
# ============================================================================
if [ "$SKIP_GIT" != true ]; then
    log_section "Step 1: Pushing to Git"

    log_info "Pushing to ${GIT_REMOTE}/${GIT_BRANCH}..."
    if run_command git push ${GIT_REMOTE} ${GIT_BRANCH} --tags; then
        log_success "Pushed to git"
    else
        log_error "Git push failed"
        [ "$DRY_RUN" != true ] && exit 1
    fi
else
    log_info "⏭️  Skipping Git Push"
fi

# ============================================================================
# STEP 2: Build Python Package
# ============================================================================
if [ "$SKIP_BUILD" != true ]; then
    log_section "Step 2: Building Python Package"

    if [ "$CLEAN_DIST" = true ]; then
        log_info "Cleaning old builds..."
        run_command rm -rf dist/
    fi

    log_info "Building package with: $BUILD_COMMAND"
    if run_command $BUILD_COMMAND; then
        log_success "Package built successfully"
        [ "$DRY_RUN" != true ] && ls -lh dist/
    else
        log_error "Build failed"
        [ "$DRY_RUN" != true ] && exit 1
    fi
else
    log_info "⏭️  Skipping Package Build"
fi

# ============================================================================
# STEP 3: Publish to PyPI
# ============================================================================
if [ "$SKIP_PYPI" != true ]; then
    log_section "Step 3: Publishing to PyPI"

    log_info "Publishing ${PACKAGE_NAME}-${VERSION} to PyPI..."

    if [ -n "$PyPI_API_TOKEN" ]; then
        if run_command $PUBLISH_COMMAND "dist/${PACKAGE_NAME}-${VERSION}"* --token "$PyPI_API_TOKEN"; then
            log_success "Published to PyPI"
        else
            log_error "PyPI publish failed"
            [ "$DRY_RUN" != true ] && exit 1
        fi
    elif [ -n "$UV_PUBLISH_TOKEN" ]; then
        if run_command $PUBLISH_COMMAND "dist/${PACKAGE_NAME}-${VERSION}"*; then
            log_success "Published to PyPI"
        else
            log_error "PyPI publish failed"
            [ "$DRY_RUN" != true ] && exit 1
        fi
    else
        log_warning "No PyPI token found, skipping publish"
        log_info "You can publish manually with:"
        log_info "  $PUBLISH_COMMAND dist/${PACKAGE_NAME}-${VERSION}* --token YOUR_TOKEN"
    fi

    if [ "$DRY_RUN" != true ]; then
        log_info "Waiting ${PYPI_WAIT_SECONDS} seconds for PyPI to process..."
        sleep ${PYPI_WAIT_SECONDS}
    fi
else
    log_info "⏭️  Skipping PyPI Publish"
fi

# ============================================================================
# STEP 4: Install Latest Version Locally
# ============================================================================
if [ "$SKIP_INSTALL" != true ]; then
    log_section "Step 4: Installing Latest Version Locally"

    log_info "Installing ${PACKAGE_NAME}==${VERSION}..."
    if run_command $INSTALL_COMMAND $INSTALL_METHOD "${PACKAGE_NAME}==${VERSION}"; then
        log_success "Installed locally"
    else
        log_warning "Local install failed"
        [ "$DRY_RUN" != true ] && exit 1
    fi
else
    log_info "⏭️  Skipping Local Install"
fi

# ============================================================================
# STEP 5-7: Plugin Updates (Optional)
# ============================================================================
if [ "$SKIP_PLUGINS" != true ]; then
    if [ "$CLAUDE_PLUGIN_ENABLED" = true ]; then
        log_section "Step 5: Updating Claude Plugin"
        if command -v claude &> /dev/null; then
            log_info "Updating Claude plugin..."
            run_command claude plugin update "$PACKAGE_NAME" || log_warning "Claude plugin update failed"
        else
            log_warning "Claude CLI not found"
        fi
    fi

    if [ "$GEMINI_EXTENSION_ENABLED" = true ] && [ -d "$GEMINI_EXTENSION_DIR" ]; then
        log_section "Step 6: Updating Gemini Extension"
        log_info "Updating Gemini extension version to ${VERSION}..."
        # Add your Gemini extension update logic here
    fi

    if [ "$CODEX_SKILL_ENABLED" = true ]; then
        log_section "Step 7: Updating Codex Skill"
        log_info "Codex skill update logic goes here"
    fi
else
    log_info "⏭️  Skipping Plugin Updates"
fi

# ============================================================================
# Summary
# ============================================================================
log_section "Deployment Complete! 🎉"

echo ""
echo "Summary:"
echo "--------"
echo "✅ Version: $VERSION"
echo "✅ Package: ${PACKAGE_NAME}"
echo ""
log_success "Deployment finished successfully!"
echo ""
echo "Verify deployment:"
echo "  - PyPI: ${PYPI_PROJECT_URL}${VERSION}/"
echo "  - Local: python -c 'import ${PACKAGE_NAME}; print(${PACKAGE_NAME}.__version__)'"
echo ""
