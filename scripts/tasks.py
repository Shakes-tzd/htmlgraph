"""
Invoke tasks for deployment automation.

Provides Python-native alternative to deploy-all.sh shell script.
Run with: invoke --list (see available tasks)
          invoke deploy --version=0.8.0 (deploy specific version)
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Optional

from invoke import task
import tomllib  # Python 3.11+ built-in TOML parser


# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
PACKAGE_NAME = "htmlgraph"
PYTHON_VERSION_FILE = PROJECT_ROOT / "src/python/htmlgraph/__init__.py"

# Plugin configuration
CLAUDE_PLUGIN_ENABLED = True
GEMINI_EXTENSION_ENABLED = True
CODEX_SKILL_ENABLED = False
GEMINI_EXTENSION_DIR = PROJECT_ROOT / "packages/gemini-extension"
GEMINI_CONFIG_FILE = GEMINI_EXTENSION_DIR / "gemini-extension.json"

# Git configuration
GIT_REMOTE = "origin"
GIT_BRANCH = "main"
PYPI_WAIT_SECONDS = 10

# Build/install configuration
BUILD_COMMAND = "uv build"
INSTALL_COMMAND = "pip install"
PUBLISH_COMMAND = "uv publish"


# ============================================================================
# Utility Functions
# ============================================================================


def get_version_from_pyproject() -> str:
    """Extract version from pyproject.toml"""
    with open(PYPROJECT_TOML, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def run_command(
    cmd: list[str], check: bool = True, dry_run: bool = False, verbose: bool = True
) -> int:
    """Run a command, optionally in dry-run mode"""
    cmd_str = " ".join(cmd)
    if dry_run:
        print(f"[DRY-RUN] Would run: {cmd_str}")
        return 0
    if verbose:
        print(f"Running: {cmd_str}")
    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        print(f"Error: Command failed with code {result.returncode}")
        sys.exit(1)
    return result.returncode


def log_section(title: str) -> None:
    """Print a section header"""
    print(f"\n{'=' * 70}")
    print(f"{title:^70}")
    print(f"{'=' * 70}\n")


def log_success(msg: str) -> None:
    """Print a success message"""
    print(f"✅ {msg}")


def log_error(msg: str) -> None:
    """Print an error message"""
    print(f"❌ {msg}")


def log_warning(msg: str) -> None:
    """Print a warning message"""
    print(f"⚠️  {msg}")


def log_info(msg: str) -> None:
    """Print an info message"""
    print(f"ℹ️  {msg}")


# ============================================================================
# Invoke Tasks
# ============================================================================


@task
def push_git(ctx, dry_run=False):
    """Push commits and tags to git remote"""
    log_section("Step 1: Pushing to Git")

    log_info(f"Pushing to {GIT_REMOTE}/{GIT_BRANCH}...")

    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "diff-index", "--quiet", "HEAD", "--"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        log_warning("You have uncommitted changes")
        subprocess.run(["git", "status", "--short"], cwd=PROJECT_ROOT)
        if not dry_run:
            response = input("Continue anyway? (y/n) ")
            if response.lower() != "y":
                print("Aborted")
                return

    run_command(
        ["git", "push", GIT_REMOTE, GIT_BRANCH, "--tags"],
        cwd=PROJECT_ROOT,
        dry_run=dry_run,
    )
    log_success("Pushed to git")


@task
def build_package(ctx, dry_run=False):
    """Build Python package distribution"""
    log_section("Step 2: Building Python Package")

    log_info("Cleaning old builds...")
    dist_dir = PROJECT_ROOT / "dist"
    if dist_dir.exists() and not dry_run:
        import shutil
        shutil.rmtree(dist_dir)

    log_info("Building package...")
    run_command([BUILD_COMMAND], cwd=PROJECT_ROOT, dry_run=dry_run)

    if not dry_run and dist_dir.exists():
        files = list(dist_dir.glob("*"))
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {f.name} ({size_mb:.2f} MB)")

    log_success("Package built successfully")


@task
def publish_pypi(ctx, version: Optional[str] = None, dry_run=False):
    """Publish package to PyPI"""
    log_section("Step 3: Publishing to PyPI")

    if version is None:
        version = get_version_from_pyproject()

    log_info(f"Publishing {PACKAGE_NAME}-{version} to PyPI...")

    # Check for PyPI token
    token_env = "UV_PUBLISH_TOKEN"
    if token_env not in ctx.os.environ:
        log_warning("PyPI token not found in environment")
        log_info(f"Set {token_env} environment variable to publish")
        if not dry_run:
            response = input("Continue anyway? (y/n) ")
            if response.lower() != "y":
                print("Aborted")
                return

    dist_pattern = f"dist/{PACKAGE_NAME}-{version}*"
    run_command(
        [PUBLISH_COMMAND, dist_pattern],
        cwd=PROJECT_ROOT,
        dry_run=dry_run,
    )

    if not dry_run:
        log_info(f"Waiting {PYPI_WAIT_SECONDS} seconds for PyPI to process...")
        import time
        time.sleep(PYPI_WAIT_SECONDS)

    log_success("Published to PyPI")


@task
def install_local(ctx, version: Optional[str] = None, dry_run=False):
    """Install latest version locally"""
    log_section("Step 4: Installing Latest Version Locally")

    if version is None:
        version = get_version_from_pyproject()

    log_info(f"Installing {PACKAGE_NAME}=={version}...")

    run_command(
        [INSTALL_COMMAND, "--upgrade", f"{PACKAGE_NAME}=={version}"],
        cwd=PROJECT_ROOT,
        dry_run=dry_run,
    )

    if not dry_run:
        # Verify installation
        try:
            import htmlgraph
            installed_version = htmlgraph.__version__
            if installed_version == version:
                log_success(f"Verified: {PACKAGE_NAME} {installed_version} is installed")
            else:
                log_warning(
                    f"Installed version ({installed_version}) doesn't match "
                    f"expected ({version})"
                )
        except ImportError:
            log_warning("Could not verify installation")
    else:
        log_success("Install (dry-run skipped)")


@task
def update_claude_plugin(ctx, dry_run=False):
    """Update Claude plugin"""
    log_section("Step 5: Updating Claude Plugin")

    if not CLAUDE_PLUGIN_ENABLED:
        log_info("⏭️  Claude plugin updates disabled in config")
        return

    # Check if claude CLI exists
    result = subprocess.run(["which", "claude"], check=False, capture_output=True)
    if result.returncode != 0:
        log_warning("Claude CLI not found")
        log_info("Install with: npm install -g @anthropics/claude-cli")
        return

    log_info(f"Updating Claude plugin ({PACKAGE_NAME})...")
    run_command(
        ["claude", "plugin", "update", PACKAGE_NAME],
        cwd=PROJECT_ROOT,
        dry_run=dry_run,
    )
    log_success("Claude plugin updated")


@task
def update_gemini_extension(ctx, version: Optional[str] = None, dry_run=False):
    """Update Gemini extension"""
    log_section("Step 6: Updating Gemini Extension")

    if not GEMINI_EXTENSION_ENABLED:
        log_info("⏭️  Gemini extension updates disabled in config")
        return

    if not GEMINI_EXTENSION_DIR.exists():
        log_warning(f"Gemini extension directory not found: {GEMINI_EXTENSION_DIR}")
        return

    if version is None:
        version = get_version_from_pyproject()

    log_info(f"Updating Gemini extension version to {version}...")

    config_file = GEMINI_EXTENSION_DIR / "gemini-extension.json"
    if not config_file.exists():
        log_warning(f"Config file not found: {config_file}")
        return

    if not dry_run:
        with open(config_file, "r") as f:
            config = json.load(f)

        config["version"] = version

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        log_success(f"Gemini extension version updated to {version}")
    else:
        log_info(f"[DRY-RUN] Would update gemini-extension.json to version {version}")

    # Run deploy script if it exists
    deploy_script = GEMINI_EXTENSION_DIR / "deploy.sh"
    if deploy_script.exists():
        log_info("Running Gemini extension deploy script...")
        run_command(
            ["bash", "deploy.sh"],
            cwd=GEMINI_EXTENSION_DIR,
            dry_run=dry_run,
        )
    else:
        log_info("No deploy script found for Gemini extension")


@task
def update_codex_skill(ctx, dry_run=False):
    """Update Codex skill (if applicable)"""
    log_section("Step 7: Updating Codex Skill")

    if not CODEX_SKILL_ENABLED:
        log_info("⏭️  Codex skill updates disabled in config")
        return

    # Check if codex CLI exists
    result = subprocess.run(["which", "codex"], check=False, capture_output=True)
    if result.returncode != 0:
        log_info("Codex CLI not found - skipping")
        return

    log_info("Checking for Codex skill...")
    log_info("Codex skill update - manual verification needed")


# ============================================================================
# Main Deployment Task
# ============================================================================


@task
def deploy(
    ctx,
    version: Optional[str] = None,
    docs_only: bool = False,
    build_only: bool = False,
    skip_pypi: bool = False,
    skip_plugins: bool = False,
    dry_run: bool = False,
):
    """
    Deploy HtmlGraph package.

    Options:
        --version=X.Y.Z     Version to deploy (auto-detected from pyproject.toml)
        --docs-only         Only commit and push to git
        --build-only        Only build package
        --skip-pypi         Skip PyPI publishing
        --skip-plugins      Skip plugin updates
        --dry-run           Show what would happen without executing

    Examples:
        invoke deploy                               # Full deployment
        invoke deploy --version=0.8.0              # Deploy specific version
        invoke deploy --docs-only                  # Just push to git
        invoke deploy --build-only                 # Just build package
        invoke deploy --skip-pypi                  # Build but don't publish
        invoke deploy --dry-run                    # Preview actions
    """

    if version is None:
        version = get_version_from_pyproject()

    log_section(f"HtmlGraph Deployment - Version {version}")

    if dry_run:
        log_warning("DRY-RUN MODE - No actual changes will be made")

    # Validate project root
    if not PYPROJECT_TOML.exists():
        log_error("Must be run from project root (where pyproject.toml is)")
        sys.exit(1)

    try:
        # Determine which steps to run
        if docs_only:
            log_info("Running in DOCS-ONLY mode")
            push_git(ctx, dry_run=dry_run)
        elif build_only:
            log_info("Running in BUILD-ONLY mode")
            build_package(ctx, dry_run=dry_run)
        else:
            # Full deployment
            push_git(ctx, dry_run=dry_run)
            build_package(ctx, dry_run=dry_run)

            if not skip_pypi:
                publish_pypi(ctx, version=version, dry_run=dry_run)
                install_local(ctx, version=version, dry_run=dry_run)
            else:
                log_info("⏭️  Skipping PyPI Publish")
                log_info("⏭️  Skipping Local Install")

            if not skip_plugins:
                if CLAUDE_PLUGIN_ENABLED:
                    update_claude_plugin(ctx, dry_run=dry_run)
                if GEMINI_EXTENSION_ENABLED:
                    update_gemini_extension(ctx, version=version, dry_run=dry_run)
                if CODEX_SKILL_ENABLED:
                    update_codex_skill(ctx, dry_run=dry_run)
            else:
                log_info("⏭️  Skipping Plugin Updates")

        # Summary
        log_section("Deployment Complete! 🎉")
        log_success("All deployment steps completed successfully!")

        if not dry_run:
            print(f"\nVerify deployment:")
            print(f"  - PyPI: https://pypi.org/project/{PACKAGE_NAME}/{version}/")
            print(f"  - GitHub: https://github.com/Shakes-tzd/{PACKAGE_NAME}")
            print(f"  - Local: python -c 'import {PACKAGE_NAME}; print({PACKAGE_NAME}.__version__)'")

    except Exception as e:
        log_error(f"Deployment failed: {e}")
        sys.exit(1)


# ============================================================================
# Utility Tasks
# ============================================================================


@task
def get_version(ctx):
    """Get current version from pyproject.toml"""
    version = get_version_from_pyproject()
    print(f"Current version: {version}")
