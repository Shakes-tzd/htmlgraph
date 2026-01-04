#!/usr/bin/env python3
"""
HtmlGraph CLI.

Usage:
    htmlgraph serve [--port PORT] [--dir DIR]
    htmlgraph init [DIR]
    htmlgraph status [--dir DIR]
    htmlgraph query SELECTOR [--dir DIR]

Claude Code Integration:
    htmlgraph claude                    # Start Claude Code
    htmlgraph claude --init             # Start with orchestrator system prompt (recommended)
    htmlgraph claude --continue         # Resume last Claude Code session (with plugin loaded)
    htmlgraph claude --dev              # Start in development mode (load plugin from packages/)

Session Management:
    htmlgraph session start [--id ID] [--agent AGENT]
    htmlgraph session end ID [--notes NOTES] [--recommend NEXT] [--blocker BLOCKER]
    htmlgraph session list
    htmlgraph session start-info [--agent AGENT] [--format json]  # Optimized session start (1 call)
    htmlgraph session handoff [--session-id ID] [--notes NOTES] [--recommend NEXT] [--blocker BLOCKER] [--show]
    htmlgraph activity TOOL SUMMARY [--session ID] [--files FILE...]

Feature Management:
    htmlgraph feature start ID
    htmlgraph feature complete ID
    htmlgraph feature primary ID
    htmlgraph feature claim ID
    htmlgraph feature release ID
    htmlgraph feature auto-release

Track Management (Conductor-Style Planning):
    htmlgraph track new TITLE [--priority PRIORITY]
    htmlgraph track list
    htmlgraph track spec TRACK_ID TITLE
    htmlgraph track plan TRACK_ID TITLE
    htmlgraph track delete TRACK_ID

Analytics:
    htmlgraph analytics                           # Project-wide analytics
    htmlgraph analytics --session-id SESSION_ID   # Single session analysis
    htmlgraph analytics --recent N                # Analyze recent N sessions
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def create_json_response(
    command: str,
    data: dict | list,
    success: bool = True,
    metadata: dict | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict:
    """Create standardized JSON response for CLI commands."""
    import htmlgraph

    return {
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "version": htmlgraph.__version__,
        "command": command,
        "data": data,
        "metadata": metadata or {},
        "warnings": warnings or [],
        "errors": errors or [],
    }


def cmd_install_gemini_extension(args: argparse.Namespace) -> None:
    """Install the Gemini CLI extension from the bundled package files."""
    import htmlgraph

    # Find the extension path in the installed package
    package_dir = Path(htmlgraph.__file__).parent
    extension_dir = package_dir / "extensions" / "gemini"

    if not extension_dir.exists():
        print(f"Error: Gemini extension not found at {extension_dir}", file=sys.stderr)
        print(
            "The extension may not be bundled with this version of htmlgraph.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Installing Gemini extension from: {extension_dir}")

    # Run gemini extensions install with the bundled path
    try:
        result = subprocess.run(
            ["gemini", "extensions", "install", str(extension_dir), "--consent"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        print("\n✅ Gemini extension installed successfully!")
        print("\nTo verify installation:")
        print("  gemini extensions list")
    except subprocess.CalledProcessError as e:
        print(f"Error installing extension: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gemini' command not found.", file=sys.stderr)
        print("Please install Gemini CLI first:", file=sys.stderr)
        print("  npm install -g @google/gemini-cli", file=sys.stderr)
        sys.exit(1)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the HtmlGraph server."""
    from htmlgraph.operations import start_server

    start_server(
        port=args.port,
        graph_dir=args.graph_dir,
        static_dir=args.static_dir,
        host=args.host,
        watch=not args.no_watch,
        auto_port=args.auto_port,
    )

    # The start_server operation already handles all output and blocks
    # No additional CLI formatting needed


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a new .htmlgraph directory."""
    import shutil
    from contextlib import nullcontext

    from htmlgraph.analytics_index import AnalyticsIndex
    from htmlgraph.server import HtmlGraphAPIHandler

    # Interactive setup wizard
    if args.interactive:
        print("=== HtmlGraph Interactive Setup ===\n")

        # Get project name
        default_name = Path(args.dir).resolve().name
        project_name = input(f"Project name [{default_name}]: ").strip() or default_name

        # Get agent name
        agent_name = input("Your agent name [claude]: ").strip() or "claude"

        # Ask about git hooks
        install_hooks_response = (
            input("Install git hooks for automatic tracking? [Y/n]: ").strip().lower()
        )
        args.install_hooks = install_hooks_response != "n"

        # Ask about documentation generation
        gen_docs_response = (
            input("Generate AGENTS.md, CLAUDE.md, GEMINI.md? [Y/n]: ").strip().lower()
        )
        generate_docs = gen_docs_response != "n"

        print()
    else:
        # Non-interactive defaults
        project_name = Path(args.dir).resolve().name
        agent_name = "claude"
        generate_docs = True  # Always generate in non-interactive mode

    def init_progress() -> tuple[Any | None, Any | None]:
        if getattr(args, "quiet", False) or getattr(args, "format", "text") != "text":
            return None, None
        try:
            from rich.console import Console
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeElapsedColumn,
            )
        except Exception:
            return None, None
        console = Console()
        progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        )
        return progress, console

    graph_dir = Path(args.dir) / ".htmlgraph"
    events_dir = graph_dir / "events"

    def ensure_gitignore_entries(project_dir: Path, lines: list[str]) -> None:
        if args.no_update_gitignore:
            return
        gitignore_path = project_dir / ".gitignore"
        existing = ""
        if gitignore_path.exists():
            try:
                existing = gitignore_path.read_text(encoding="utf-8")
            except Exception:
                existing = ""
        existing_lines = set(existing.splitlines())
        missing = [ln for ln in lines if ln not in existing_lines]
        if not missing:
            return
        block = "\n".join(
            ["", "# HtmlGraph analytics index (rebuildable cache)", *missing, ""]
            if "# HtmlGraph analytics index (rebuildable cache)" not in existing_lines
            else ["", *missing, ""]
        )
        try:
            gitignore_path.write_text(existing + block, encoding="utf-8")
        except Exception:
            # Don't fail init on .gitignore issues.
            pass

    progress, progress_console = init_progress()

    def status_context(message: str) -> Any:
        if progress_console is None:
            return nullcontext()
        return progress_console.status(message)

    # Hook templates (used when htmlgraph is installed without this repo layout).
    post_commit = """#!/bin/bash
#
# HtmlGraph Post-Commit Hook
# Logs Git commit events for agent-agnostic continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events commit &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event commit &> /dev/null &
exit 0
"""

    post_checkout = """#!/bin/bash
#
# HtmlGraph Post-Checkout Hook
# Logs branch switches / checkouts for continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

OLD_HEAD="$1"
NEW_HEAD="$2"
FLAG="$3"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events checkout "$OLD_HEAD" "$NEW_HEAD" "$FLAG" &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event checkout "$OLD_HEAD" "$NEW_HEAD" "$FLAG" &> /dev/null &
exit 0
"""

    post_merge = """#!/bin/bash
#
# HtmlGraph Post-Merge Hook
# Logs successful merges for continuity tracking
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

SQUASH_FLAG="$1"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    python3 -m htmlgraph.git_events merge "$SQUASH_FLAG" &> /dev/null &
  fi
  exit 0
fi

htmlgraph git-event merge "$SQUASH_FLAG" &> /dev/null &
exit 0
"""

    pre_push = """#!/bin/bash
#
# HtmlGraph Pre-Push Hook
# Logs pushes for continuity tracking / team boundary events
#

set +e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 0

if [ ! -d ".htmlgraph" ]; then
  exit 0
fi

REMOTE_NAME="$1"
REMOTE_URL="$2"
UPDATES="$(cat)"

if ! command -v htmlgraph &> /dev/null; then
  if command -v python3 &> /dev/null; then
    printf "%s" "$UPDATES" | python3 -m htmlgraph.git_events push "$REMOTE_NAME" "$REMOTE_URL" &> /dev/null &
  fi
  exit 0
fi

printf "%s" "$UPDATES" | htmlgraph git-event push "$REMOTE_NAME" "$REMOTE_URL" &> /dev/null &
exit 0
"""

    pre_commit = """#!/bin/bash
#
# HtmlGraph Pre-Commit Hook
# 1. BLOCKS direct edits to .htmlgraph/ (AI agents must use SDK)
# 2. Reminds developers to create/start features for non-trivial work
#
# To disable feature reminder: git config htmlgraph.precommit false
# To bypass blocking once: git commit --no-verify (NOT RECOMMENDED)

# Check if HtmlGraph is initialized
if [ ! -d ".htmlgraph" ]; then
    # Not an HtmlGraph project, skip silently
    exit 0
fi

# Redirect output to stderr (standard for git hooks)
exec 1>&2

# ============================================================
# BLOCKING CHECK: Direct edits to .htmlgraph/ files
# AI agents must use SDK, not direct file edits
# ============================================================
HTMLGRAPH_FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep "^\\.htmlgraph/" || true)

if [ -n "$HTMLGRAPH_FILES" ]; then
    echo ""
    echo "❌ BLOCKED: Direct edits to .htmlgraph/ files"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Modified files:"
    echo "$HTMLGRAPH_FILES" | while read -r file; do
        echo "  - $file"
    done
    echo ""
    echo "AI agents must use SDK, not direct file edits."
    echo "See AGENTS.md line 3: 'AI agents must NEVER edit .htmlgraph/ HTML files directly'"
    echo ""
    echo "Use SDK instead:"
    echo "  from htmlgraph import SDK"
    echo "  sdk = SDK()"
    echo "  sdk.features.complete('feature-id')  # Mark feature done"
    echo "  sdk.features.create('Title')         # Create new feature"
    echo ""
    echo "Or CLI:"
    echo "  uv run htmlgraph feature complete <id>"
    echo "  uv run htmlgraph feature create 'Title'"
    echo ""
    echo "To bypass (NOT RECOMMENDED): git commit --no-verify"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exit 1
fi

# ============================================================
# REMINDER CHECK: Feature tracking (non-blocking)
# ============================================================
# Check if reminder is disabled via config
if [ "$(git config --type=bool htmlgraph.precommit)" = "false" ]; then
    exit 0
fi

# Fast check for in-progress features using grep (avoids Python startup)
ACTIVE_COUNT=$(find .htmlgraph/features -name "*.html" -exec grep -l 'data-status="in-progress"' {} \\; 2>/dev/null | wc -l | tr -d ' ')

# If we have active features and htmlgraph CLI is available, get details
if [ "$ACTIVE_COUNT" -gt 0 ] && command -v htmlgraph &> /dev/null; then
    ACTIVE_FEATURES=$(htmlgraph feature list --status in-progress 2>/dev/null)
else
    ACTIVE_FEATURES=""
fi

if [ "$ACTIVE_COUNT" -gt 0 ]; then
    echo ""
    echo "✓ HtmlGraph: $ACTIVE_COUNT active feature(s)"
    echo ""
    echo "$ACTIVE_FEATURES"
    echo ""
else
    echo ""
    echo "⚠️  HtmlGraph Feature Reminder"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "No active features found. Did you forget to start one?"
    echo ""
    echo "Quick decision:"
    echo "  • >30 min work? → Create feature"
    echo "  • 3+ files? → Create feature"
    echo "  • Simple fix? → Direct commit OK"
    echo ""
    echo "To disable: git config htmlgraph.precommit false"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

exit 0
"""

    hook_files: dict[str, Path] = {}

    def create_graph_dirs() -> None:
        graph_dir.mkdir(parents=True, exist_ok=True)
        for collection in HtmlGraphAPIHandler.COLLECTIONS:
            (graph_dir / collection).mkdir(exist_ok=True)

    def create_events_dir() -> None:
        events_dir.mkdir(exist_ok=True)
        if not args.no_events_keep:
            keep = events_dir / ".gitkeep"
            if not keep.exists():
                keep.write_text("", encoding="utf-8")

    def copy_assets() -> None:
        styles_src = Path(__file__).parent / "styles.css"
        styles_dest = graph_dir / "styles.css"
        if styles_src.exists() and not styles_dest.exists():
            styles_dest.write_text(styles_src.read_text())

        index_path = Path(args.dir) / "index.html"
        if not index_path.exists():
            create_default_index(index_path)

    def init_analytics_cache() -> None:
        if args.no_index:
            return
        with status_context("Initializing analytics cache..."):
            try:
                AnalyticsIndex(graph_dir / "index.sqlite").ensure_schema()
            except Exception:
                # Never fail init because of analytics cache.
                pass

    def update_gitignore() -> None:
        ensure_gitignore_entries(
            Path(args.dir),
            [
                ".htmlgraph/index.sqlite",
                ".htmlgraph/index.sqlite-wal",
                ".htmlgraph/index.sqlite-shm",
                ".htmlgraph/git-hook-errors.log",
            ],
        )

    def create_hook_templates() -> None:
        nonlocal hook_files
        hooks_dir = graph_dir / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        def ensure_hook_file(hook_name: str, hook_content: str) -> Path:
            hook_dest = hooks_dir / f"{hook_name}.sh"
            if not hook_dest.exists():
                hook_dest.write_text(hook_content)
            try:
                hook_dest.chmod(0o755)
            except Exception:
                pass
            return hook_dest

        hook_files = {
            "pre-commit": ensure_hook_file("pre-commit", pre_commit),
            "post-commit": ensure_hook_file("post-commit", post_commit),
            "post-checkout": ensure_hook_file("post-checkout", post_checkout),
            "post-merge": ensure_hook_file("post-merge", post_merge),
            "pre-push": ensure_hook_file("pre-push", pre_push),
        }

    def generate_docs_step() -> None:
        if not generate_docs:
            return

        def render_template(
            template_path: Path, replacements: dict[str, str]
        ) -> str | None:
            """Render a template file with variable replacements."""
            if not template_path.exists():
                return None
            content = template_path.read_text(encoding="utf-8")
            for key, value in replacements.items():
                content = content.replace(f"{{{{{key}}}}}", value)
            return content

        templates_dir = Path(__file__).parent / "templates"
        project_dir = Path(args.dir)

        # Get version
        try:
            from htmlgraph import __version__

            version = __version__
        except Exception:
            version = "unknown"

        replacements = {
            "PROJECT_NAME": project_name,
            "AGENT_NAME": agent_name,
            "VERSION": version,
        }

        # Generate AGENTS.md
        agents_template = templates_dir / "AGENTS.md.template"
        agents_dest = project_dir / "AGENTS.md"
        if agents_template.exists() and not agents_dest.exists():
            content = render_template(agents_template, replacements)
            if content:
                agents_dest.write_text(content, encoding="utf-8")
                print(f"✓ Generated: {agents_dest}")

        # Generate CLAUDE.md
        claude_template = templates_dir / "CLAUDE.md.template"
        claude_dest = project_dir / "CLAUDE.md"
        if claude_template.exists() and not claude_dest.exists():
            content = render_template(claude_template, replacements)
            if content:
                claude_dest.write_text(content, encoding="utf-8")
                print(f"✓ Generated: {claude_dest}")

        # Generate GEMINI.md
        gemini_template = templates_dir / "GEMINI.md.template"
        gemini_dest = project_dir / "GEMINI.md"
        if gemini_template.exists() and not gemini_dest.exists():
            content = render_template(gemini_template, replacements)
            if content:
                gemini_dest.write_text(content, encoding="utf-8")
                print(f"✓ Generated: {gemini_dest}")

    def install_hooks_step() -> None:
        if not args.install_hooks:
            return
        git_dir = Path(args.dir) / ".git"
        if not git_dir.exists():
            print("\n⚠️  Warning: No .git directory found. Git hooks not installed.")
            print("   Initialize git first: git init")
            return

        def install_hook(
            hook_name: str, hook_dest: Path, hook_content: str | None
        ) -> None:
            """
            Install one Git hook:
              - Ensure `.htmlgraph/hooks/<hook>.sh` exists (copy template if present; else inline)
              - Install to `.git/hooks/<hook>` (symlink or chained wrapper if existing)
            """
            # Try to copy a template from this repo layout (dev), otherwise inline.
            hook_src = (
                Path(__file__).parent.parent.parent.parent
                / ".htmlgraph"
                / "hooks"
                / f"{hook_name}.sh"
            )
            if hook_src.exists() and hook_src.resolve() != hook_dest.resolve():
                shutil.copy(hook_src, hook_dest)
            elif not hook_dest.exists():
                if not hook_content:
                    raise RuntimeError(f"Missing hook content for {hook_name}")
                hook_dest.write_text(hook_content)
            # Ensure executable (covers the case where the file already existed)
            try:
                hook_dest.chmod(0o755)
            except Exception:
                pass

            git_hook_path = git_dir / "hooks" / hook_name

            if git_hook_path.exists():
                print(f"\n⚠️  Existing {hook_name} hook found")
                backup_path = git_hook_path.with_suffix(".existing")
                if not backup_path.exists():
                    shutil.copy(git_hook_path, backup_path)
                    print(f"   Backed up to: {backup_path}")

                chain_content = f'''#!/bin/bash
# Chained hook - runs existing hook then HtmlGraph hook

if [ -f "{backup_path}" ]; then
  "{backup_path}" || exit $?
fi

if [ -f "{hook_dest}" ]; then
  "{hook_dest}" || true
fi
'''
                git_hook_path.write_text(chain_content)
                git_hook_path.chmod(0o755)
                print(f"   Installed chained hook at: {git_hook_path}")
                return

            try:
                git_hook_path.symlink_to(hook_dest.resolve())
                print("\n✓ Git hooks installed")
                print(f"  {hook_name}: {git_hook_path} -> {hook_dest}")
            except OSError:
                shutil.copy(hook_dest, git_hook_path)
                git_hook_path.chmod(0o755)
                print("\n✓ Git hooks installed")
                print(f"  {hook_name}: {git_hook_path}")

        install_hook("pre-commit", hook_files["pre-commit"], pre_commit)
        install_hook("post-commit", hook_files["post-commit"], post_commit)
        install_hook("post-checkout", hook_files["post-checkout"], post_checkout)
        install_hook("post-merge", hook_files["post-merge"], post_merge)
        install_hook("pre-push", hook_files["pre-push"], pre_push)

        print("\nGit events will now be logged to HtmlGraph automatically.")

    steps: list[tuple[str, Any]] = [
        ("Create .htmlgraph directories", create_graph_dirs),
        ("Create event log directory", create_events_dir),
        ("Update .gitignore", update_gitignore),
        ("Prepare git hook templates", create_hook_templates),
        ("Copy default assets", copy_assets),
    ]
    if not args.no_index:
        steps.append(("Initialize analytics cache", init_analytics_cache))
    if generate_docs:
        steps.append(("Generate documentation", generate_docs_step))
    if args.install_hooks:
        steps.append(("Install git hooks", install_hooks_step))

    def run_steps(step_list: list[tuple[str, Any]]) -> None:
        if progress is None:
            for _, fn in step_list:
                fn()
            return

        with progress:
            task_id = progress.add_task(
                "Initializing HtmlGraph...", total=len(step_list)
            )
            for description, fn in step_list:
                progress.update(task_id, description=description)
                fn()
                progress.advance(task_id)

    run_steps(steps)

    print(f"\nInitialized HtmlGraph in {graph_dir}")
    print(f"Collections: {', '.join(HtmlGraphAPIHandler.COLLECTIONS)}")
    print("\nStart server with: htmlgraph serve")
    if not args.no_index:
        print(
            f"Analytics cache: {graph_dir / 'index.sqlite'} (rebuildable; typically gitignored)"
        )
    print(f"Events: {events_dir}/ (append-only JSONL)")


def cmd_install_hooks(args: argparse.Namespace) -> None:
    """Install Git hooks for automatic tracking."""
    from pathlib import Path

    from htmlgraph.hooks import AVAILABLE_HOOKS
    from htmlgraph.hooks.installer import HookConfig, HookInstaller

    project_dir = Path(args.project_dir).resolve()

    # Load configuration
    config_path = project_dir / ".htmlgraph" / "hooks-config.json"
    config = HookConfig(config_path)

    # Handle configuration changes
    if args.enable:
        if args.enable not in AVAILABLE_HOOKS:
            print(f"Error: Unknown hook '{args.enable}'")
            print(f"Available hooks: {', '.join(AVAILABLE_HOOKS)}")
            return
        config.enable_hook(args.enable)
        config.save()
        print(f"✓ Enabled hook '{args.enable}' in configuration")
        return

    if args.disable:
        if args.disable not in AVAILABLE_HOOKS:
            print(f"Error: Unknown hook '{args.disable}'")
            print(f"Available hooks: {', '.join(AVAILABLE_HOOKS)}")
            return
        config.disable_hook(args.disable)
        config.save()
        print(f"✓ Disabled hook '{args.disable}' in configuration")
        return

    # Override symlink preference if --use-copy is set
    if args.use_copy:
        config.config["use_symlinks"] = False

    # Create installer
    installer = HookInstaller(project_dir, config)

    # Validate environment
    is_valid, error_msg = installer.validate_environment()
    if not is_valid:
        print(f"❌ {error_msg}")
        return

    # List hooks status
    if args.list:
        print("\nGit Hooks Installation Status")
        print("=" * 60)

        status = installer.list_hooks()
        for hook_name, info in status.items():
            status_icon = "✓" if info["installed"] else "✗"
            enabled_icon = "🟢" if info["enabled"] else "🔴"

            print(f"\n{enabled_icon} {hook_name} ({status_icon} installed)")
            print(f"  Enabled in config: {info['enabled']}")
            print(f"  Versioned (.htmlgraph/hooks/): {info['versioned']}")
            print(f"  Installed (.git/hooks/): {info['installed']}")

            if info["is_symlink"]:
                our_hook = "✓" if info.get("our_hook", False) else "✗"
                print(f"  Type: Symlink ({our_hook} ours)")
                print(f"  Target: {info.get('symlink_target', 'unknown')}")
            elif info["installed"]:
                print("  Type: Copied file")

        print("\n" + "=" * 60)
        print(f"\nConfiguration: {config_path}")
        print("Use 'htmlgraph install-hooks --enable <hook>' to enable")
        print("Use 'htmlgraph install-hooks --disable <hook>' to disable")
        return

    # Uninstall a hook
    if args.uninstall:
        if args.uninstall not in AVAILABLE_HOOKS:
            print(f"Error: Unknown hook '{args.uninstall}'")
            print(f"Available hooks: {', '.join(AVAILABLE_HOOKS)}")
            return

        success, message = installer.uninstall_hook(args.uninstall)
        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
        return

    # Install hooks
    print("\n🔧 Installing Git hooks for HtmlGraph\n")
    print(f"Project: {project_dir}")
    print(f"Configuration: {config_path}")

    if args.dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    results = installer.install_all_hooks(force=args.force, dry_run=args.dry_run)

    # Display results
    success_count = 0
    failure_count = 0

    for hook_name, (success, message) in results.items():
        if success:
            success_count += 1
            print(f"✓ {message}")
        else:
            failure_count += 1
            print(f"❌ {message}")

    print("\n" + "=" * 60)
    print(f"Summary: {success_count} installed, {failure_count} failed")

    if not args.dry_run:
        print(f"\nConfiguration saved to: {config_path}")
        print("\nGit events will now be logged to HtmlGraph automatically.")
        print("\nManagement commands:")
        print("  htmlgraph install-hooks --list          # Show status")
        print("  htmlgraph install-hooks --uninstall <hook>  # Remove hook")
        print("  htmlgraph install-hooks --enable <hook>     # Enable hook")
        print("  htmlgraph install-hooks --disable <hook>    # Disable hook")


def cmd_status(args: argparse.Namespace) -> None:
    """Show status of the graph."""
    import json
    from collections import Counter

    from htmlgraph.sdk import SDK

    # Use SDK to query all collections
    sdk = SDK(directory=args.graph_dir)

    total = 0
    by_status: Counter[str] = Counter()
    by_collection = {}

    # All available collections
    collections = [
        "features",
        "bugs",
        "chores",
        "spikes",
        "epics",
        "phases",
        "sessions",
        "tracks",
        "agents",
    ]

    for coll_name in collections:
        coll = getattr(sdk, coll_name)
        try:
            nodes = coll.all()
            count = len(nodes)
            if count > 0:
                by_collection[coll_name] = count
                total += count

                # Count by status
                for node in nodes:
                    status = getattr(node, "status", "unknown")
                    by_status[status] += 1
        except Exception:
            # Collection might not exist yet
            pass

    # Output based on format flag
    if args.format == "json":
        response = create_json_response(
            command="status",
            data={
                "total_nodes": total,
                "by_collection": dict(sorted(by_collection.items())),
                "by_status": dict(sorted(by_status.items())),
            },
            metadata={"graph_dir": args.graph_dir},
        )
        print(json.dumps(response, indent=2))
    else:
        # Text output (default)
        if not args.quiet:
            print(f"HtmlGraph Status: {args.graph_dir}")
            print(f"{'=' * 40}")

        print(f"Total nodes: {total}")

        if not args.quiet:
            print("\nBy Collection:")
            for coll, count in sorted(by_collection.items()):
                print(f"  {coll}: {count}")
            print("\nBy Status:")
            for status, count in sorted(by_status.items()):
                print(f"  {status}: {count}")

        # Verbose output
        if args.verbose >= 1:
            print("\n--- Verbose Details ---")
            print(f"Graph directory: {args.graph_dir}")
            print(f"Collections scanned: {len(collections)}")
            print(f"Collections with data: {len(by_collection)}")

        if args.verbose >= 2:
            print("\nAll collections checked:")
            for coll_name in collections:
                count = by_collection.get(coll_name, 0)
                marker = "✓" if count > 0 else "○"
                print(f"  {marker} {coll_name}: {count}")


def cmd_debug(args: argparse.Namespace) -> None:
    """Show debugging resources and system diagnostics."""
    import os
    from pathlib import Path

    from htmlgraph.sdk import SDK

    print("🔍 HtmlGraph Debugging Resources\n")
    print("=" * 60)

    # Documentation
    print("\n📚 Documentation:")
    print("  - DEBUGGING.md - Complete debugging guide")
    print("  - AGENTS.md - SDK and agent documentation")
    print("  - CLAUDE.md - Project workflow")

    # Debugging Agents
    print("\n🤖 Debugging Agents:")
    agents_dir = Path("packages/claude-plugin/agents")
    if agents_dir.exists():
        print(f"  - {agents_dir}/researcher.md")
        print(f"  - {agents_dir}/debugger.md")
        print(f"  - {agents_dir}/test-runner.md")
    else:
        print("  - researcher.md - Research documentation before implementing")
        print("  - debugger.md - Systematic error analysis")
        print("  - test-runner.md - Quality gates and validation")

    # Diagnostic Commands
    print("\n🛠️  Diagnostic Commands:")
    print("  htmlgraph status              - Show current graph state")
    print("  htmlgraph feature list        - List all features")
    print("  htmlgraph session list        - List all sessions")
    print("  htmlgraph analytics           - Project analytics")

    # Current System Status
    print("\n📊 Current Status:")
    print(f"  Graph directory: {args.graph_dir}")

    graph_path = Path(args.graph_dir)
    if graph_path.exists():
        print("  Status: ✅ Initialized")

        # Try to get quick stats
        try:
            sdk = SDK(directory=args.graph_dir)

            # Count features
            features = sdk.features.all()
            print(f"  Features: {len(features)}")

            # Count sessions
            sessions = sdk.sessions.all()
            print(f"  Sessions: {len(sessions)}")

            # Count other collections
            for coll_name in ["bugs", "chores", "spikes", "epics", "phases", "tracks"]:
                try:
                    coll = getattr(sdk, coll_name)
                    nodes = coll.all()
                    if len(nodes) > 0:
                        print(f"  {coll_name.capitalize()}: {len(nodes)}")
                except Exception:
                    pass

        except Exception as e:
            print(f"  Warning: Could not load graph data: {e}")
    else:
        print("  Status: ⚠️  Not initialized")
        print("  Run 'htmlgraph init' to create .htmlgraph directory")

    # Environment Info
    print("\n🔧 Environment:")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working dir: {os.getcwd()}")

    # Check for common files
    print("\n📁 Project Files:")
    for filename in ["pyproject.toml", "package.json", ".git", "README.md"]:
        exists = "✅" if Path(filename).exists() else "❌"
        print(f"  {exists} {filename}")

    print("\n" + "=" * 60)
    print("For more help: https://github.com/Shakes-tzd/htmlgraph")
    print()


def cmd_query(args: argparse.Namespace) -> None:
    """Query nodes with CSS selector."""
    import json

    from htmlgraph.converter import node_to_dict
    from htmlgraph.graph import HtmlGraph

    graph_dir = Path(args.graph_dir)
    if not graph_dir.exists():
        print(f"Error: {graph_dir} not found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for collection_dir in graph_dir.iterdir():
        if collection_dir.is_dir() and not collection_dir.name.startswith("."):
            graph = HtmlGraph(collection_dir, auto_load=True)
            for node in graph.query(args.selector):
                data = node_to_dict(node)
                data["_collection"] = collection_dir.name
                results.append(data)

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        for result in results:  # type: dict[str, Any]
            status = result.get("status", "?")
            priority = result.get("priority", "?")
            print(
                f"[{result['_collection']}] {result['id']}: {result['title']} ({status}, {priority})"
            )


# =============================================================================
# Session Management Commands
# =============================================================================


def cmd_session_start(args: argparse.Namespace) -> None:
    """Start a new session."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    session = sdk.start_session(session_id=args.id, title=args.title, agent=args.agent)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict

        print(json.dumps(session_to_dict(session), indent=2))
    else:
        print(f"Session started: {session.id}")
        print(f"  Agent: {session.agent}")
        print(f"  Started: {session.started_at.isoformat()}")
        if session.title:
            print(f"  Title: {session.title}")


def cmd_session_end(args: argparse.Namespace) -> None:
    """End a session."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir)
    blockers = args.blocker if args.blocker else None
    session = sdk.end_session(
        args.id,
        handoff_notes=args.notes,
        recommended_next=args.recommend,
        blockers=blockers,
    )

    if session is None:
        print(f"Error: Session '{args.id}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict

        print(json.dumps(session_to_dict(session), indent=2))
    else:
        print(f"Session ended: {session.id}")
        print(f"  Duration: {session.ended_at - session.started_at}")
        print(f"  Events: {session.event_count}")
        if session.worked_on:
            print(f"  Worked on: {', '.join(session.worked_on)}")


def cmd_session_handoff(args: argparse.Namespace) -> None:
    """Set or show session handoff context."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    if args.show:
        # For showing, we might still need direct manager access or add more methods to SDK
        # But for now, let's keep using SessionManager logic via SDK property if needed
        # or implement show logic here using SDK collections

        # Use session_manager.get_session() to get Session objects (not Node)
        if args.session_id:
            session = sdk.session_manager.get_session(args.session_id)
        else:
            # Need "last ended session" - SDK doesn't expose this yet.
            # Fallback to session_manager logic exposed on SDK
            session = sdk.session_manager.get_last_ended_session(agent=args.agent)

        if not session:
            if args.format == "json":
                print(json.dumps({}))
            else:
                print("No handoff context found.")
            return

        if args.format == "json":
            from htmlgraph.converter import session_to_dict

            print(json.dumps(session_to_dict(session), indent=2))
        else:
            print(f"Session: {session.id}")
            if session.handoff_notes:
                print(f"Notes: {session.handoff_notes}")
            if session.recommended_next:
                print(f"Recommended next: {session.recommended_next}")
            if session.blockers:
                print(f"Blockers: {', '.join(session.blockers)}")
        return

    # Setting handoff
    if not (args.notes or args.recommend or args.blocker):
        print(
            "Error: Provide --notes, --recommend, or --blocker (or use --show).",
            file=sys.stderr,
        )
        sys.exit(1)

    handoff_result = sdk.set_session_handoff(
        session_id=args.session_id,  # Optional, defaults to active
        handoff_notes=args.notes,
        recommended_next=args.recommend,
        blockers=args.blocker if args.blocker else None,
    )

    if handoff_result is None:
        if args.session_id:
            print(f"Error: Session '{args.session_id}' not found.", file=sys.stderr)
        else:
            print(
                "Error: No active session found. Provide --session-id.",
                file=sys.stderr,
            )
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(handoff_result, indent=2))
    else:
        print(f"Session handoff updated: {handoff_result.get('id', 'unknown')}")


def cmd_session_list(args: argparse.Namespace) -> None:
    """List all sessions."""
    import json

    from htmlgraph.converter import SessionConverter

    sessions_dir = Path(args.graph_dir) / "sessions"
    if not sessions_dir.exists():
        print("No sessions found.")
        return

    converter = SessionConverter(sessions_dir)
    sessions = converter.load_all()

    # Sort by started_at descending (handle mixed tz-aware/naive datetimes)
    def sort_key(s: Any) -> Any:
        ts = s.started_at
        # Make naive datetimes comparable by assuming UTC
        if ts.tzinfo is None:
            return ts.replace(tzinfo=None)
        return ts.replace(tzinfo=None)  # Compare as naive for sorting

    sessions.sort(key=sort_key, reverse=True)

    if args.format == "json":
        from htmlgraph.converter import session_to_dict

        print(json.dumps([session_to_dict(s) for s in sessions], indent=2))
    else:
        if not sessions:
            print("No sessions found.")
            return

        print(f"{'ID':<30} {'Status':<10} {'Agent':<15} {'Events':<8} {'Started'}")
        print("=" * 90)
        for session in sessions:
            started = session.started_at.strftime("%Y-%m-%d %H:%M")
            print(
                f"{session.id:<30} {session.status:<10} {session.agent:<15} {session.event_count:<8} {started}"
            )


def cmd_session_start_info(args: argparse.Namespace) -> None:
    """Get comprehensive session start information (optimized for AI agents)."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    info = sdk.get_session_start_info(
        include_git_log=not args.no_git,
        git_log_count=args.git_count,
        analytics_top_n=args.top_n,
        analytics_max_agents=args.max_agents,
    )

    if args.format == "json":
        print(json.dumps(info, indent=2, default=str))
    else:
        # Human-readable format
        status = info["status"]
        print("=" * 80)
        print("SESSION START INFO")
        print("=" * 80)

        # Project status
        print(f"\nProject: {status.get('project_name', 'HtmlGraph')}")
        print(f"Total nodes: {status.get('total_nodes', 0)}")
        print(f"In progress: {status.get('in_progress_count', 0)}")
        print(f"Completed: {status.get('done_count', 0)}")

        # Active work item (validation status)
        active_work = info.get("active_work")
        print("\nACTIVE WORK:")
        if active_work:
            # Determine type symbol
            type_symbol = {
                "feature": "✨",
                "bug": "🐛",
                "spike": "🔍",
                "chore": "🔧",
                "epic": "🎯",
            }.get(active_work.get("type"), "📝")

            # Build progress info
            steps_total = active_work.get("steps_total", 0)
            steps_completed = active_work.get("steps_completed", 0)
            progress_str = (
                f"({steps_completed}/{steps_total} steps)" if steps_total > 0 else ""
            )

            # Check if auto-spike
            auto_spike_info = ""
            if active_work.get("type") == "spike" and active_work.get("auto_generated"):
                spike_subtype = active_work.get("spike_subtype", "unknown")
                auto_spike_info = f" [AUTO-{spike_subtype.upper()}]"

            print(
                f"  {type_symbol} {active_work['id']}: {active_work['title']} {progress_str}{auto_spike_info}"
            )
        else:
            print("  ⚠️  No active work item")
            print("  Code changes will be blocked until you assign work.")
            print('  Create a feature: uv run htmlgraph feature create "Title"')

        # Active features
        active_features = [f for f in info["features"] if f["status"] == "in-progress"]
        if active_features:
            print(f"\nACTIVE FEATURES ({len(active_features)}):")
            for feat in active_features:
                progress = (
                    f"{feat['steps_completed']}/{feat['steps_total']}"
                    if feat["steps_total"] > 0
                    else "no steps"
                )
                print(f"  - {feat['id']}: {feat['title']} ({progress})")

        # Recent sessions
        recent_sessions = info["sessions"][:5]
        if recent_sessions:
            print(f"\nRECENT SESSIONS ({len(recent_sessions)}):")
            for sess in recent_sessions:
                print(
                    f"  - {sess['id']}: {sess['agent']} ({sess['event_count']} events)"
                )

        # Git log
        if info.get("git_log"):
            print("\nRECENT COMMITS:")
            for commit in info["git_log"]:
                print(f"  {commit}")

        # Analytics
        analytics = info["analytics"]

        # Bottlenecks
        bottlenecks = analytics.get("bottlenecks", [])
        if bottlenecks:
            print(f"\nBOTTLENECKS ({len(bottlenecks)}):")
            for bn in bottlenecks:
                print(
                    f"  - {bn['title']} (blocks {bn['blocks_count']} tasks, impact: {bn['impact_score']:.1f})"
                )

        # Recommendations
        recommendations = analytics.get("recommendations", [])
        if recommendations:
            print("\nRECOMMENDATIONS:")
            for rec in recommendations[:3]:
                reasons_str = ", ".join(rec["reasons"][:2])
                print(f"  - {rec['title']} (score: {rec['score']:.1f})")
                print(f"    Why: {reasons_str}")
                if rec.get("unlocks_count", 0) > 0:
                    print(f"    Unlocks: {rec['unlocks_count']} tasks")

        # Parallel capacity
        parallel = analytics.get("parallel", {})
        if parallel:
            print("\nPARALLEL CAPACITY:")
            print(f"  Max parallelism: {parallel.get('max_parallelism', 0)}")
            print(f"  Ready now: {parallel.get('ready_now', 0)}")
            print(f"  Total ready: {parallel.get('total_ready', 0)}")

        print("\n" + "=" * 80)


def cmd_session_status_report(args: argparse.Namespace) -> None:
    """Print a comprehensive status report (Markdown)."""
    import subprocess

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir)
    status = sdk.get_status()

    # Git log
    try:
        git_log = subprocess.check_output(
            ["git", "log", "--oneline", "-n", "3"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        git_log = "(Git log unavailable)"

    # Active features detail
    active_features_text = ""
    if status["active_features"]:
        active_features_text = "\n### Current Feature(s)\n"
        for fid in status["active_features"]:
            # Use SDK to get nodes
            node = sdk.features.get(fid) or sdk.bugs.get(fid)
            if node:
                active_features_text += f"**Working On:** {node.title} ({node.id})\n"
                active_features_text += f"**Status:** {node.status}\n"
                if node.steps:
                    active_features_text += "**Step Progress**\n"
                    for step in node.steps:
                        mark = "[x]" if step.completed else "[ ]"
                        active_features_text += f"- {mark} {step.description}\n"
                active_features_text += "\n"
    else:
        active_features_text = "\n### Current Feature(s)\nNo active features. Start one with `htmlgraph feature start <id>`.\n"

    # Project Name (from directory)
    project_name = Path(args.graph_dir).resolve().parent.name

    completed = status["by_status"].get("done", 0)
    total = status["total_features"]
    pct = int(completed / max(1, total) * 100)

    print(f"""## Session Status

**Project:** {project_name}
**Progress:** {completed}/{total} features ({pct}%)
**Active Features (WIP):** {status["wip_count"]}

---
{active_features_text}---

### Recent Commits
{git_log}

---

### What's Next
Use `htmlgraph feature list --status todo` to see backlog.
""")


def cmd_session_dedupe(args: argparse.Namespace) -> None:
    """Move low-signal session files out of the main sessions directory."""
    from htmlgraph import SDK

    sdk = SDK(directory=args.graph_dir)
    result = sdk.dedupe_sessions(
        max_events=args.max_events,
        move_dir_name=args.move_dir,
        dry_run=args.dry_run,
        stale_extra_active=not args.no_stale_active,
    )

    print(f"Scanned: {result['scanned']}")
    print(f"Moved:   {result['moved']}")
    if result.get("missing"):
        print(f"Missing: {result['missing']}")
    if not args.dry_run:
        if result.get("staled_active"):
            print(f"Staled:  {result['staled_active']} extra active sessions")
        if result.get("kept_active"):
            print(f"Kept:    {result['kept_active']} canonical active sessions")


def cmd_session_link(args: argparse.Namespace) -> None:
    """Link a feature to a session retroactively."""
    import json

    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Edge

    graph_dir = Path(args.graph_dir)
    sessions_dir = graph_dir / "sessions"
    feature_dir = graph_dir / args.collection

    # Load session
    session_file = sessions_dir / f"{args.session_id}.html"
    if not session_file.exists():
        print(
            f"Error: Session '{args.session_id}' not found at {session_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    session_graph = HtmlGraph(sessions_dir)
    session = session_graph.get(args.session_id)
    if not session:
        print(f"Error: Failed to load session '{args.session_id}'", file=sys.stderr)
        sys.exit(1)

    # Load feature
    feature_file = feature_dir / f"{args.feature_id}.html"
    if not feature_file.exists():
        print(
            f"Error: Feature '{args.feature_id}' not found at {feature_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    feature_graph = HtmlGraph(feature_dir)
    feature = feature_graph.get(args.feature_id)
    if not feature:
        print(f"Error: Failed to load feature '{args.feature_id}'", file=sys.stderr)
        sys.exit(1)

    # Check if already linked
    worked_on = session.edges.get("worked-on", [])
    already_linked = any(e.target_id == args.feature_id for e in worked_on)

    if already_linked:
        print(
            f"Feature '{args.feature_id}' is already linked to session '{args.session_id}'"
        )
        if not args.bidirectional:
            sys.exit(0)

    # Add edge from session to feature
    if not already_linked:
        new_edge = Edge(
            target_id=args.feature_id, relationship="worked-on", title=feature.title
        )
        if "worked-on" not in session.edges:
            session.edges["worked-on"] = []
        session.edges["worked-on"].append(new_edge)
        session_graph.update(session)
        print(f"✓ Linked feature '{args.feature_id}' to session '{args.session_id}'")

    # Optionally add reciprocal edge from feature to session
    if args.bidirectional:
        implemented_in = feature.edges.get("implemented-in", [])
        feature_already_linked = any(
            e.target_id == args.session_id for e in implemented_in
        )

        if not feature_already_linked:
            reciprocal_edge = Edge(
                target_id=args.session_id,
                relationship="implemented-in",
                title=f"Session {session.id}",
            )
            if "implemented-in" not in feature.edges:
                feature.edges["implemented-in"] = []
            feature.edges["implemented-in"].append(reciprocal_edge)
            feature_graph.update(feature)
            print(
                f"✓ Added reciprocal link from feature '{args.feature_id}' to session '{args.session_id}'"
            )
        else:
            print(f"Feature '{args.feature_id}' already has reciprocal link to session")

    if args.format == "json":
        result = {
            "session_id": args.session_id,
            "feature_id": args.feature_id,
            "bidirectional": args.bidirectional,
            "linked": not already_linked,
        }
        print(json.dumps(result, indent=2))


def cmd_session_validate_attribution(args: argparse.Namespace) -> None:
    """Validate feature attribution and tracking."""
    import json
    from datetime import datetime

    from htmlgraph.graph import HtmlGraph

    graph_dir = Path(args.graph_dir)
    feature_dir = graph_dir / args.collection
    sessions_dir = graph_dir / "sessions"
    events_dir = graph_dir / "events"

    # Load feature
    feature_graph = HtmlGraph(feature_dir)
    feature = feature_graph.get(args.feature_id)
    if not feature:
        print(f"Error: Feature '{args.feature_id}' not found", file=sys.stderr)
        sys.exit(1)

    # Find sessions that worked on this feature
    sessions_graph = HtmlGraph(sessions_dir)
    all_sessions = sessions_graph.query('[data-type="session"]')
    linked_sessions = []

    for session in all_sessions:
        worked_on = session.edges.get("worked-on", [])
        if any(e.target_id == args.feature_id for e in worked_on):
            linked_sessions.append(session)

    # Count events attributed to this feature
    event_count = 0
    last_activity = None
    high_drift_events = []

    for session in linked_sessions:
        session_events_file = events_dir / f"{session.id}.jsonl"
        if session_events_file.exists():
            with open(session_events_file) as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get("feature_id") == args.feature_id:
                            event_count += 1
                            timestamp = event.get("timestamp")
                            if timestamp:
                                event_time = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                                if not last_activity or event_time > last_activity:
                                    last_activity = event_time

                            # Check for high drift
                            drift_score = event.get("drift_score")
                            if drift_score and drift_score > 0.8:
                                high_drift_events.append(
                                    {
                                        "timestamp": timestamp,
                                        "tool": event.get("tool"),
                                        "drift": drift_score,
                                    }
                                )
                    except json.JSONDecodeError:
                        continue

    # Calculate attribution health
    health = "UNKNOWN"
    issues = []

    if len(linked_sessions) == 0:
        health = "CRITICAL"
        issues.append("Feature not linked to any session")
    elif event_count == 0:
        health = "CRITICAL"
        issues.append("No events attributed to feature")
    elif event_count < 5:
        health = "WARNING"
        issues.append(f"Only {event_count} events attributed (unusually low)")
    else:
        health = "GOOD"

    if len(high_drift_events) > 3:
        if health == "GOOD":
            health = "WARNING"
        issues.append(
            f"{len(high_drift_events)} events with drift > 0.8 (may be misattributed)"
        )

    # Output results
    if args.format == "json":
        result = {
            "feature_id": args.feature_id,
            "feature_title": feature.title,
            "health": health,
            "linked_sessions": len(linked_sessions),
            "event_count": event_count,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "high_drift_count": len(high_drift_events),
            "issues": issues,
        }
        print(json.dumps(result, indent=2))
    else:
        status_symbol = "✓" if health == "GOOD" else "⚠" if health == "WARNING" else "✗"
        print(f"{status_symbol} Feature '{args.feature_id}' validation:")
        print(f"  Title: {feature.title}")
        print(f"  Health: {health}")
        print(f"  - Linked to {len(linked_sessions)} session(s)")
        print(f"  - {event_count} events attributed")
        if last_activity:
            print(f"  - Last activity: {last_activity.strftime('%Y-%m-%d %H:%M:%S')}")

        if issues:
            print("\n⚠ Issues detected:")
            for issue in issues:
                print(f"  - {issue}")

        if len(high_drift_events) > 0 and len(high_drift_events) <= 5:
            print("\n⚠ High drift events:")
            for event in high_drift_events[:5]:
                print(
                    f"  - {event['timestamp']}: {event['tool']} (drift: {event['drift']:.2f})"
                )


# =========================================================================
# Transcript Commands
# =========================================================================


def cmd_transcript_list(args: argparse.Namespace) -> None:
    """List available Claude Code transcripts."""
    import json

    from htmlgraph.transcript import TranscriptReader

    reader = TranscriptReader()

    # Use project path filter if provided
    project_path = args.project if hasattr(args, "project") and args.project else None

    sessions = reader.list_sessions(
        project_path=project_path,
        limit=args.limit if hasattr(args, "limit") else 20,
    )

    if not sessions:
        if args.format == "json":
            print(json.dumps({"sessions": [], "count": 0}))
        else:
            print("No Claude Code transcripts found.")
            print(f"\nLooked in: {reader.claude_dir}")
        return

    if args.format == "json":
        data = {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "path": str(s.path),
                    "cwd": s.cwd,
                    "git_branch": s.git_branch,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "user_messages": s.user_message_count,
                    "tool_calls": s.tool_call_count,
                    "duration_seconds": s.duration_seconds,
                }
                for s in sessions
            ],
            "count": len(sessions),
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Found {len(sessions)} Claude Code transcript(s):\n")
        for s in sessions:
            started = (
                s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "unknown"
            )
            duration = f"{int(s.duration_seconds / 60)}m" if s.duration_seconds else "?"
            branch = s.git_branch or "no branch"
            print(
                f"  {s.session_id[:12]}  {started}  {duration:>6}  {s.user_message_count:>3} msgs  [{branch}]"
            )


def cmd_transcript_import(args: argparse.Namespace) -> None:
    """Import a Claude Code transcript into HtmlGraph."""
    import json

    from htmlgraph.session_manager import SessionManager
    from htmlgraph.transcript import TranscriptReader

    reader = TranscriptReader()
    manager = SessionManager(args.graph_dir)

    # Find the transcript
    transcript = reader.read_session(args.session_id)
    if not transcript:
        print(f"Error: Transcript not found: {args.session_id}", file=sys.stderr)
        sys.exit(1)

    # Find or create HtmlGraph session to import into
    htmlgraph_session_id = args.to_session
    if not htmlgraph_session_id:
        # Check if already linked
        existing = manager.find_session_by_transcript(args.session_id)
        if existing:
            htmlgraph_session_id = existing.id
            print(f"Found existing linked session: {htmlgraph_session_id}")
        else:
            # Create a new session
            agent = args.agent or "claude-code"
            new_session = manager.start_session(
                agent=agent,
                title=f"Imported: {transcript.session_id[:12]}",
            )
            htmlgraph_session_id = new_session.id
            print(f"Created new session: {htmlgraph_session_id}")

    # Import events
    result = manager.import_transcript_events(
        session_id=htmlgraph_session_id,
        transcript_session=transcript,
        overwrite=args.overwrite if hasattr(args, "overwrite") else False,
    )

    # Link to feature if specified
    if args.link_feature:
        session = manager.get_session(htmlgraph_session_id)
        if session and args.link_feature not in session.worked_on:
            session.worked_on.append(args.link_feature)
            manager.session_converter.save(session)
            result["linked_feature"] = args.link_feature

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"✅ Imported transcript {args.session_id[:12]}:")
        print(f"   → HtmlGraph session: {htmlgraph_session_id}")
        print(f"   → Events imported: {result.get('imported', 0)}")
        print(f"   → Events skipped: {result.get('skipped', 0)}")
        if result.get("linked_feature"):
            print(f"   → Linked to feature: {result['linked_feature']}")


def cmd_transcript_link(args: argparse.Namespace) -> None:
    """Link a Claude Code transcript to an HtmlGraph session."""
    import json

    from htmlgraph.session_manager import SessionManager
    from htmlgraph.transcript import TranscriptReader

    reader = TranscriptReader()
    manager = SessionManager(args.graph_dir)

    # Find the transcript to get git branch
    transcript = reader.read_session(args.session_id)
    if not transcript:
        print(f"Error: Transcript not found: {args.session_id}", file=sys.stderr)
        sys.exit(1)

    # Link to HtmlGraph session
    session = manager.link_transcript(
        session_id=args.to_session,
        transcript_id=args.session_id,
        transcript_path=str(transcript.path),
        git_branch=transcript.git_branch,
    )

    if not session:
        print(f"Error: HtmlGraph session not found: {args.to_session}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "linked": True,
                    "session_id": session.id,
                    "transcript_id": args.session_id,
                    "git_branch": transcript.git_branch,
                },
                indent=2,
            )
        )
    else:
        print(f"✅ Linked transcript {args.session_id[:12]} to session {session.id}")
        if transcript.git_branch:
            print(f"   Git branch: {transcript.git_branch}")


def cmd_transcript_stats(args: argparse.Namespace) -> None:
    """Show transcript statistics for a session."""
    import json

    from htmlgraph.session_manager import SessionManager

    manager = SessionManager(args.graph_dir)
    stats = manager.get_transcript_stats(args.session_id)

    if not stats:
        print(
            f"Error: No transcript linked to session: {args.session_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    if stats.get("error"):
        print(f"Error: {stats['error']}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(stats, indent=2))
    else:
        print(f"Transcript Stats for {args.session_id}:")
        print(f"  Transcript ID: {stats['transcript_id']}")
        print(f"  Git Branch: {stats.get('git_branch', 'N/A')}")
        print(f"  User Messages: {stats['user_messages']}")
        print(f"  Tool Calls: {stats['tool_calls']}")
        if stats.get("duration_seconds"):
            mins = int(stats["duration_seconds"] / 60)
            print(f"  Duration: {mins} minutes")
        print(f"  Has Thinking Traces: {stats['has_thinking_traces']}")
        if stats.get("tool_breakdown"):
            print("  Tool Breakdown:")
            for tool, count in sorted(
                stats["tool_breakdown"].items(), key=lambda x: -x[1]
            ):
                print(f"    {tool}: {count}")


def cmd_transcript_auto_link(args: argparse.Namespace) -> None:
    """Auto-link transcripts to sessions by git branch."""
    import json

    from htmlgraph.session_manager import SessionManager

    manager = SessionManager(args.graph_dir)

    # Get current git branch if not specified
    branch = args.branch
    if not branch:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()
        except Exception:
            print(
                "Error: Could not detect git branch. Specify with --branch",
                file=sys.stderr,
            )
            sys.exit(1)

    linked = manager.auto_link_transcript_by_branch(
        git_branch=branch,
        agent=args.agent,
    )

    if args.format == "json":
        print(
            json.dumps(
                {
                    "branch": branch,
                    "linked": [
                        {"session_id": s, "transcript_id": t} for s, t in linked
                    ],
                    "count": len(linked),
                },
                indent=2,
            )
        )
    else:
        if linked:
            print(f"✅ Auto-linked {len(linked)} session(s) for branch '{branch}':")
            for session_id, transcript_id in linked:
                print(f"   {session_id} ← {transcript_id[:12]}")
        else:
            print(f"No sessions to link for branch '{branch}'")


def cmd_transcript_health(args: argparse.Namespace) -> None:
    """Show session health metrics from transcript."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    health = analytics.calculate_session_health(args.transcript_id)

    if not health:
        print(
            f"Error: Could not analyze transcript {args.transcript_id}", file=sys.stderr
        )
        sys.exit(1)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "session_id": health.session_id,
                    "overall_score": round(health.overall_score(), 2),
                    "efficiency_score": round(health.efficiency_score, 2),
                    "retry_rate": round(health.retry_rate, 2),
                    "context_rebuild_count": health.context_rebuild_count,
                    "tool_diversity": round(health.tool_diversity, 2),
                    "prompt_clarity_score": round(health.prompt_clarity_score, 2),
                    "error_recovery_rate": round(health.error_recovery_rate, 2),
                    "duration_seconds": round(health.duration_seconds, 1),
                    "tools_per_minute": round(health.tools_per_minute, 1),
                },
                indent=2,
            )
        )
    else:
        score = health.overall_score()
        grade = (
            "🟢 Excellent"
            if score > 0.8
            else "🟡 Good"
            if score > 0.6
            else "🟠 Fair"
            if score > 0.4
            else "🔴 Needs Work"
        )

        print(f"Session Health: {args.transcript_id[:12]}...")
        print(f"{'=' * 50}")
        print(f"Overall Score: {score:.0%} {grade}")
        print()
        print(f"📊 Efficiency:      {health.efficiency_score:.0%}")
        print(
            f"🔄 Retry Rate:      {health.retry_rate:.0%} {'⚠️' if health.retry_rate > 0.3 else '✓'}"
        )
        print(
            f"📚 Context Rebuilds: {health.context_rebuild_count} {'⚠️' if health.context_rebuild_count > 5 else '✓'}"
        )
        print(f"🔧 Tool Diversity:  {health.tool_diversity:.0%}")
        print(f"💬 Prompt Clarity:  {health.prompt_clarity_score:.0%}")
        print(f"🔧 Error Recovery:  {health.error_recovery_rate:.0%}")
        print()
        dur_mins = int(health.duration_seconds // 60)
        dur_secs = int(health.duration_seconds % 60)
        print(
            f"⏱️  Duration: {dur_mins}m {dur_secs}s | Tools/min: {health.tools_per_minute:.1f}"
        )


def cmd_transcript_patterns(args: argparse.Namespace) -> None:
    """Detect workflow patterns in transcripts."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    patterns = analytics.detect_patterns(
        transcript_id=args.transcript_id,
        min_length=args.min_length,
        max_length=args.max_length,
    )

    if args.format == "json":
        print(
            json.dumps(
                [
                    {
                        "sequence": p.sequence,
                        "count": p.count,
                        "category": p.category,
                    }
                    for p in patterns
                ],
                indent=2,
            )
        )
    else:
        print("Workflow Patterns Detected")
        print("=" * 50)

        optimal = [p for p in patterns if p.category == "optimal"]
        anti = [p for p in patterns if p.category == "anti-pattern"]
        neutral = [p for p in patterns if p.category == "neutral"][:10]

        if optimal:
            print("\n✅ Optimal Patterns:")
            for p in optimal:
                print(f"   {' → '.join(p.sequence)} ({p.count}x)")

        if anti:
            print("\n⚠️ Anti-Patterns:")
            for p in anti:
                print(f"   {' → '.join(p.sequence)} ({p.count}x)")

        if neutral:
            print("\n📊 Common Patterns:")
            for p in neutral:
                print(f"   {' → '.join(p.sequence)} ({p.count}x)")


def cmd_transcript_transitions(args: argparse.Namespace) -> None:
    """Show tool transition matrix."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    transitions = analytics.get_tool_transitions(transcript_id=args.transcript_id)

    if args.format == "json":
        print(json.dumps(transitions, indent=2))
    else:
        print("Tool Transition Matrix")
        print("=" * 50)
        print("(from_tool → to_tool: count)")
        print()

        # Flatten and sort
        flat = []
        for from_tool, tos in transitions.items():
            for to_tool, count in tos.items():
                flat.append((from_tool, to_tool, count))

        flat.sort(key=lambda x: -x[2])

        for from_t, to_t, count in flat[:20]:
            bar = "█" * min(count, 20)
            print(f"  {from_t:12} → {to_t:12} {count:4} {bar}")


def cmd_transcript_recommendations(args: argparse.Namespace) -> None:
    """Get workflow improvement recommendations."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    recommendations = analytics.generate_recommendations(
        transcript_id=args.transcript_id
    )

    if args.format == "json":
        print(json.dumps({"recommendations": recommendations}, indent=2))
    else:
        print("Workflow Recommendations")
        print("=" * 50)
        for rec in recommendations:
            print(f"  {rec}")


def cmd_transcript_insights(args: argparse.Namespace) -> None:
    """Get comprehensive transcript insights."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    insights = analytics.get_insights()

    if args.format == "json":
        print(
            json.dumps(
                {
                    "total_sessions": insights.total_sessions,
                    "total_user_messages": insights.total_user_messages,
                    "total_tool_calls": insights.total_tool_calls,
                    "tool_frequency": insights.tool_frequency,
                    "avg_session_health": round(insights.avg_session_health, 2),
                    "recommendations": insights.recommendations,
                },
                indent=2,
            )
        )
    else:
        print("📊 Transcript Insights")
        print("=" * 50)
        print(f"Sessions Analyzed: {insights.total_sessions}")
        print(f"Total User Messages: {insights.total_user_messages}")
        print(f"Total Tool Calls: {insights.total_tool_calls}")
        print(f"Avg Session Health: {insights.avg_session_health:.0%}")
        print()

        if insights.tool_frequency:
            print("🔧 Top Tools:")
            for tool, count in list(insights.tool_frequency.items())[:8]:
                bar = "█" * min(count // 5, 15)
                print(f"   {tool:15} {count:4} {bar}")

        print()
        print("💡 Recommendations:")
        for rec in insights.recommendations[:5]:
            print(f"   {rec}")


def cmd_transcript_export(args: argparse.Namespace) -> None:
    """Export transcript to HTML format."""
    from pathlib import Path

    from htmlgraph.transcript import TranscriptReader

    reader = TranscriptReader()
    transcript = reader.read_session(args.transcript_id)

    if not transcript:
        print(f"Transcript '{args.transcript_id}' not found.", file=sys.stderr)
        sys.exit(1)

    html = transcript.to_html(include_thinking=args.include_thinking)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)
        print(f"Exported to: {output_path}")
    else:
        print(html)


def cmd_transcript_track_stats(args: argparse.Namespace) -> None:
    """Get aggregated transcript stats for a track."""
    import json

    from htmlgraph.transcript_analytics import TranscriptAnalytics

    analytics = TranscriptAnalytics(args.graph_dir)
    stats = analytics.get_track_stats(args.track_id)

    if not stats:
        print(
            f"Track '{args.track_id}' not found or has no transcript data.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(stats.to_dict(), indent=2))
    else:
        print(f"📊 Track Transcript Stats: {args.track_id}")
        print("=" * 50)
        print(f"Sessions: {stats.session_count}")
        print(f"User Messages: {stats.total_user_messages}")
        print(f"Tool Calls: {stats.total_tool_calls}")
        print(f"Total Duration: {stats._format_duration(stats.total_duration_seconds)}")
        print(f"Avg Health: {stats.avg_session_health:.0%}")
        print(f"Health Trend: {stats.health_trend}")
        print(f"Anti-Patterns: {stats.anti_patterns_detected}")

        if stats.tool_frequency:
            print()
            print("🔧 Top Tools:")
            for tool, count in list(stats.tool_frequency.items())[:8]:
                bar = "█" * min(count // 5, 15)
                print(f"   {tool:15} {count:4} {bar}")

        if stats.session_ids:
            print()
            print("📂 Sessions:")
            for i, (sid, health) in enumerate(
                zip(stats.session_ids, stats.session_healths)
            ):
                print(f"   {sid[:20]:20} health: {health:.0%}")
                if i >= 9:
                    remaining = len(stats.session_ids) - 10
                    if remaining > 0:
                        print(f"   ... and {remaining} more sessions")
                    break


def cmd_transcript_link_feature(args: argparse.Namespace) -> None:
    """Link a Claude Code transcript to a feature for parallel agent tracking."""
    import json

    from htmlgraph.session_manager import SessionManager

    manager = SessionManager(args.graph_dir)
    graph = manager.features_graph

    # Get the feature
    feature = graph.get(args.to_feature)
    if not feature:
        print(f"Feature '{args.to_feature}' not found.", file=sys.stderr)
        sys.exit(1)

    # Link the transcript
    manager._link_transcript_to_feature(feature, args.transcript_id, graph)
    graph.update(feature)

    if args.format == "json":
        result = {
            "success": True,
            "feature_id": args.to_feature,
            "transcript_id": args.transcript_id,
            "tool_count": feature.properties.get("transcript_tool_count", 0),
            "duration_seconds": feature.properties.get(
                "transcript_duration_seconds", 0
            ),
        }
        print(json.dumps(result, indent=2))
    else:
        print(
            f"✅ Linked transcript '{args.transcript_id}' to feature '{args.to_feature}'"
        )
        tool_count = feature.properties.get("transcript_tool_count", 0)
        duration = feature.properties.get("transcript_duration_seconds", 0)
        if tool_count > 0:
            print(f"   Tools: {tool_count}")
            print(f"   Duration: {duration}s")


def cmd_track(args: argparse.Namespace) -> None:
    """Track an activity in the current session."""
    import json

    from htmlgraph import SDK

    agent = os.environ.get("HTMLGRAPH_AGENT")
    sdk = SDK(directory=args.graph_dir, agent=agent)

    try:
        entry = sdk.track_activity(
            tool=args.tool,
            summary=args.summary,
            file_paths=args.files,
            success=not args.failed,
            session_id=args.session,  # None if not specified, SDK will find active session
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "tool": entry.tool,
            "summary": entry.summary,
            "success": entry.success,
            "feature_id": entry.feature_id,
            "drift_score": entry.drift_score,
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Tracked: [{entry.tool}] {entry.summary}")
        if entry.feature_id:
            print(f"  Attributed to: {entry.feature_id}")
        if entry.drift_score and entry.drift_score > 0.3:
            print(f"  Drift warning: {entry.drift_score:.2f}")


# =============================================================================
# Documentation Version Management Commands
# =============================================================================


def cmd_docs_version(args: argparse.Namespace) -> None:
    """Check documentation version compatibility."""
    from htmlgraph.docs import check_docs_version

    htmlgraph_dir = Path(args.graph_dir)

    if not htmlgraph_dir.exists():
        print(f"❌ Directory not found: {htmlgraph_dir}")
        print("   Run `htmlgraph init` first")
        sys.exit(1)

    compatible, message = check_docs_version(htmlgraph_dir)

    if compatible and not message:
        print("✅ Documentation is up to date")
    elif compatible and message:
        print(message)
        print("\n💡 Run `htmlgraph docs upgrade` to update to latest version")
    else:
        print(message)
        print("\n❌ Documentation version is incompatible")
        print("   Run `htmlgraph docs upgrade` to migrate")
        sys.exit(1)


def cmd_docs_upgrade(args: argparse.Namespace) -> None:
    """Upgrade documentation to latest version."""
    from htmlgraph.docs import upgrade_docs_interactive
    from htmlgraph.docs.docs_version import get_current_doc_version
    from htmlgraph.docs.metadata import DocsMetadata
    from htmlgraph.docs.migrations import get_migration

    htmlgraph_dir = Path(args.graph_dir)

    if not htmlgraph_dir.exists():
        print(f"❌ Directory not found: {htmlgraph_dir}")
        print("   Run `htmlgraph init` first")
        sys.exit(1)

    if args.auto:
        # Auto-migrate without prompts
        metadata = DocsMetadata.load(htmlgraph_dir)
        current_version = get_current_doc_version()

        if metadata.schema_version == current_version:
            print("✅ Documentation is already up to date")
            return

        migration = get_migration(metadata.schema_version, current_version)
        if not migration:
            print(
                f"❌ No migration available from v{metadata.schema_version} to v{current_version}"
            )
            sys.exit(1)

        backup_dir = htmlgraph_dir / ".docs-backups"
        backup_dir.mkdir(exist_ok=True)

        print("🚀 Starting auto-migration...")
        success = migration.migrate(htmlgraph_dir, backup_dir)

        if success:
            print("✅ Migration complete!")
            print(f"📦 Backup saved to {backup_dir}")
        else:
            print("❌ Migration failed")
            sys.exit(1)
    else:
        # Interactive upgrade
        upgrade_docs_interactive(htmlgraph_dir)


def cmd_docs_diff(args: argparse.Namespace) -> None:
    """Show migration diff preview."""
    htmlgraph_dir = Path(args.graph_dir)

    if not htmlgraph_dir.exists():
        print(f"❌ Directory not found: {htmlgraph_dir}")
        print("   Run `htmlgraph init` first")
        sys.exit(1)

    print("📊 Showing migration preview...")
    print("⚠️  Diff preview not yet implemented")
    print("    Use `htmlgraph docs upgrade` instead")


def cmd_docs_rollback(args: argparse.Namespace) -> None:
    """Rollback to previous documentation version."""
    from htmlgraph.docs.metadata import DocsMetadata
    from htmlgraph.docs.migrations import get_migration

    htmlgraph_dir = Path(args.graph_dir)

    if not htmlgraph_dir.exists():
        print(f"❌ Directory not found: {htmlgraph_dir}")
        print("   Run `htmlgraph init` first")
        sys.exit(1)

    backup_dir = htmlgraph_dir / ".docs-backups"
    if not backup_dir.exists() or not list(backup_dir.glob("v*")):
        print("❌ No backups found")
        print("   Nothing to rollback to")
        sys.exit(1)

    # Get target version
    metadata = DocsMetadata.load(htmlgraph_dir)
    target_version = int(args.version) if args.version else metadata.schema_version - 1

    if target_version < 1:
        print("❌ Invalid version")
        sys.exit(1)

    # Get migration script
    migration = get_migration(target_version, metadata.schema_version)
    if not migration:
        print(
            f"❌ Cannot rollback from v{metadata.schema_version} to v{target_version}"
        )
        sys.exit(1)

    print(f"🔄 Rolling back to v{target_version}...")
    try:
        migration.rollback(htmlgraph_dir, backup_dir)
        print("✅ Rollback complete")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)


def cmd_docs_generate(args: argparse.Namespace) -> None:
    """Generate documentation from templates with user customizations."""
    from htmlgraph.docs import sync_docs_to_file

    htmlgraph_dir = Path(args.graph_dir)
    output_file = Path(args.output) if args.output else Path("AGENTS.md")
    platform = args.platform

    if not htmlgraph_dir.exists():
        print(f"❌ Directory not found: {htmlgraph_dir}")
        print("   Run `htmlgraph init` first")
        sys.exit(1)

    try:
        print(f"📝 Generating documentation for platform: {platform}")
        print(f"   Output: {output_file}")

        result_path = sync_docs_to_file(htmlgraph_dir, output_file, platform)

        print(f"✅ Documentation generated: {result_path}")
        print("\n💡 To customize:")
        print(f"   1. Create {htmlgraph_dir}/docs/templates/agents.md.j2")
        print("   2. Extend base template: {% extends 'base_agents.md.j2' %}")
        print("   3. Override blocks: header, introduction, custom_workflows, etc.")

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


# =============================================================================
# Events & Index Commands
# =============================================================================


def cmd_events_export(args: argparse.Namespace) -> None:
    """Export legacy session HTML activity logs to JSONL event logs."""
    from htmlgraph.event_migration import export_sessions_to_jsonl

    graph_dir = Path(args.graph_dir)
    sessions_dir = graph_dir / "sessions"
    events_dir = graph_dir / "events"

    result = export_sessions_to_jsonl(
        sessions_dir=sessions_dir,
        events_dir=events_dir,
        overwrite=args.overwrite,
        include_subdirs=args.include_subdirs,
    )

    print(f"Written: {result['written']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Failed:  {result['failed']}")


def cmd_index_rebuild(args: argparse.Namespace) -> None:
    """Rebuild the SQLite analytics index from JSONL event logs."""
    from htmlgraph.operations import rebuild_index

    graph_dir = Path(args.graph_dir)

    result = rebuild_index(graph_dir=graph_dir)

    print(f"DB: {result.db_path}")
    print(f"Inserted: {result.inserted}")
    print(f"Skipped:  {result.skipped}")


def cmd_watch(args: argparse.Namespace) -> None:
    """Watch filesystem changes and record them as activity events."""
    from htmlgraph.watch import watch_and_track

    root = Path(args.root).resolve()
    graph_dir = Path(args.graph_dir)

    watch_and_track(
        root=root,
        graph_dir=graph_dir,
        session_id=args.session_id,
        agent=args.agent,
        interval_seconds=args.interval,
        batch_seconds=args.batch_seconds,
    )


def cmd_git_event(args: argparse.Namespace) -> None:
    """Log a Git event (commit, checkout, merge, push)."""
    import sys

    from htmlgraph.git_events import (
        log_git_checkout,
        log_git_commit,
        log_git_merge,
        log_git_push,
    )

    if args.event_type == "commit":
        success = log_git_commit()
        if not success:
            sys.exit(1)
        return

    if args.event_type == "checkout":
        if len(args.args) < 3:
            print(
                "Error: checkout requires args: <old_head> <new_head> <flag>",
                file=sys.stderr,
            )
            sys.exit(1)
        old_head, new_head, flag = args.args[0], args.args[1], args.args[2]
        if not log_git_checkout(old_head, new_head, flag):
            sys.exit(1)
        return

    if args.event_type == "merge":
        squash_flag = args.args[0] if args.args else "0"
        if not log_git_merge(squash_flag):
            sys.exit(1)
        return

    if args.event_type == "push":
        if len(args.args) < 2:
            print(
                "Error: push requires args: <remote_name> <remote_url>", file=sys.stderr
            )
            sys.exit(1)
        remote_name, remote_url = args.args[0], args.args[1]
        updates_text = sys.stdin.read()
        if not log_git_push(remote_name, remote_url, updates_text):
            sys.exit(1)
        return
    else:
        print(f"Error: Unknown event type '{args.event_type}'", file=sys.stderr)
        sys.exit(1)


def cmd_mcp_serve(args: argparse.Namespace) -> None:
    """Run the minimal MCP server over stdio."""
    from htmlgraph.mcp_server import serve_stdio

    serve_stdio(graph_dir=Path(args.graph_dir), default_agent=args.agent)


# =============================================================================
# Work Management Commands (Smart Routing)
# =============================================================================


def cmd_work_next(args: argparse.Namespace) -> None:
    """Get next best task using smart routing."""
    import json

    from htmlgraph.converter import node_to_dict
    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        task = sdk.work_next(
            agent_id=args.agent, auto_claim=args.auto_claim, min_score=args.min_score
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        if task:
            print(json.dumps(node_to_dict(task), indent=2, default=str))
        else:
            print(
                json.dumps(
                    {"task": None, "message": "No suitable tasks found"}, indent=2
                )
            )
    else:
        if task:
            print(f"Next task: {task.id}")
            print(f"  Title: {task.title}")
            print(f"  Priority: {task.priority}")
            print(f"  Status: {task.status}")
            if getattr(task, "required_capabilities", None):
                print(
                    f"  Required capabilities: {', '.join(task.required_capabilities)}"
                )
            complexity = getattr(task, "complexity", None)
            if complexity:
                print(f"  Complexity: {complexity}")
            effort = getattr(task, "estimated_effort", None)
            if effort:
                print(f"  Estimated effort: {effort}h")
            if args.auto_claim:
                print(f"  ✓ Task claimed by {args.agent}")
        else:
            print("No suitable tasks found.")
            print(
                "Try lowering --min-score or check available tasks with 'htmlgraph feature list --status todo'"
            )


def cmd_work_queue(args: argparse.Namespace) -> None:
    """Get prioritized work queue for an agent."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        queue = sdk.get_work_queue(
            agent_id=args.agent, limit=args.limit, min_score=args.min_score
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps({"queue": queue, "count": len(queue)}, indent=2))
    else:
        if not queue:
            print(f"No tasks found for agent '{args.agent}'.")
            print(
                "Try lowering --min-score or check available tasks with 'htmlgraph feature list --status todo'"
            )
            return

        print(f"Work queue for {args.agent} ({len(queue)} tasks):")
        print("=" * 90)
        print(f"{'Score':<8} {'Priority':<10} {'Complexity':<12} {'ID':<25} {'Title'}")
        print("=" * 90)

        for item in queue:
            complexity = item.get("complexity", "N/A") or "N/A"
            title = (
                item["title"][:30] + "..." if len(item["title"]) > 33 else item["title"]
            )
            print(
                f"{item['score']:<8.1f} {item['priority']:<10} {complexity:<12} {item['task_id']:<25} {title}"
            )


def cmd_agent_list(args: argparse.Namespace) -> None:
    """List all registered agents."""
    import json

    from htmlgraph.agent_registry import AgentRegistry

    # Use AgentRegistry to get AgentProfile objects (not Node objects)
    registry = AgentRegistry(args.graph_dir)
    agents = list(registry.list_agents())

    if args.format == "json":
        print(
            json.dumps(
                {"agents": [agent.to_dict() for agent in agents], "count": len(agents)},
                indent=2,
            )
        )
    else:
        if not agents:
            print("No agents registered.")
            print("Agents are automatically registered in .htmlgraph/agents.json")
            return

        print(f"Registered agents ({len(agents)}):")
        print("=" * 90)

        for agent in agents:
            status = "✓ active" if agent.active else "✗ inactive"
            print(f"\n{agent.id} ({agent.name}) - {status}")
            print(f"  Capabilities: {', '.join(agent.capabilities)}")
            print(f"  Max parallel tasks: {agent.max_parallel_tasks}")
            print(f"  Preferred complexity: {', '.join(agent.preferred_complexity)}")


# =============================================================================
# Feature Management Commands
# =============================================================================


def cmd_feature_create(args: argparse.Namespace) -> None:
    """Create a new feature."""
    import json

    from htmlgraph.sdk import SDK

    # Use SDK for feature creation (which now handles logging)
    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    try:
        # Determine collection (features -> create builder, others -> manual create?)
        # For now, only 'features' has a builder in SDK.features.create()
        # But BaseCollection doesn't have create().

        # If collection is 'features', use builder
        if args.collection == "features":
            builder = sdk.features.create(
                title=args.title,
                description=args.description or "",
                priority=args.priority,
            )
            if args.steps:
                builder.add_steps(args.steps)
            node = builder.save()
        else:
            # Fallback to SessionManager directly for non-feature collections
            # (or extend SDK to support create on all collections)
            # For consistency with old CLI, we use SessionManager here if not features.
            # But wait, SDK initializes SessionManager.

            # Creating bugs/chores via SDK isn't fully fluent yet.
            # Let's use the low-level SessionManager.create_feature logic for now via SDK's session_manager
            # IF we want to strictly use SDK. But SDK.session_manager IS exposed now.
            node = sdk.session_manager.create_feature(
                title=args.title,
                collection=args.collection,
                description=args.description or "",
                priority=args.priority,
                steps=args.steps,
                agent=args.agent,
            )

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Created: {node.id}")
        print(f"  Title: {node.title}")
        print(f"  Status: {node.status}")
        print(f"  Path: {args.graph_dir}/{args.collection}/{node.id}.html")


def cmd_feature_start(args: argparse.Namespace) -> None:
    """Start working on a feature."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(
            f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr
        )
        sys.exit(1)

    try:
        node = collection.start(args.id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(
            f"Error: Feature '{args.id}' not found in {args.collection}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Started: {node.id}")
        print(f"  Title: {node.title}")
        print(f"  Status: {node.status}")

        # Show WIP status
        status = sdk.session_manager.get_status()
        print(f"  WIP: {status['wip_count']}/{status['wip_limit']}")


def cmd_feature_complete(args: argparse.Namespace) -> None:
    """Mark a feature as complete."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(
            f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr
        )
        sys.exit(1)

    try:
        node = collection.complete(args.id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(
            f"Error: Feature '{args.id}' not found in {args.collection}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Completed: {node.id}")
        print(f"  Title: {node.title}")


def cmd_feature_primary(args: argparse.Namespace) -> None:
    """Set the primary feature for attribution."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)

    # Only FeatureCollection has set_primary currently
    if args.collection == "features":
        node = sdk.features.set_primary(args.id)
    else:
        # Fallback to direct session manager for other collections
        node = sdk.session_manager.set_primary_feature(
            args.id, collection=args.collection, agent=args.agent
        )

    if node is None:
        print(
            f"Error: Feature '{args.id}' not found in {args.collection}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Primary feature set: {node.id}")
        print(f"  Title: {node.title}")


def cmd_feature_claim(args: argparse.Namespace) -> None:
    """Claim a feature."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(
            f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr
        )
        sys.exit(1)

    try:
        node = collection.claim(args.id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(
            f"Error: Feature '{args.id}' not found in {args.collection}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Claimed: {node.id}")
        print(f"  Agent: {node.agent_assigned}")
        print(f"  Session: {node.claimed_by_session}")


def cmd_feature_release(args: argparse.Namespace) -> None:
    """Release a feature."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    collection = getattr(sdk, args.collection, None)

    if not collection:
        print(
            f"Error: Collection '{args.collection}' not found in SDK.", file=sys.stderr
        )
        sys.exit(1)

    try:
        node = collection.release(args.id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if node is None:
        print(
            f"Error: Feature '{args.id}' not found in {args.collection}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format == "json":
        from htmlgraph.converter import node_to_dict

        print(json.dumps(node_to_dict(node), indent=2))
    else:
        print(f"Released: {node.id}")


def cmd_feature_auto_release(args: argparse.Namespace) -> None:
    """Release all features claimed by an agent."""
    import json

    from htmlgraph.sdk import SDK

    sdk = SDK(directory=args.graph_dir, agent=args.agent)
    # auto_release_features is on SessionManager, exposed via SDK
    released = sdk.session_manager.auto_release_features(agent=args.agent)

    if args.format == "json":
        print(json.dumps({"released": released}, indent=2))
    else:
        if not released:
            print(f"No features claimed by agent '{args.agent}'.")
        else:
            print(f"Released {len(released)} feature(s):")
            for node_id in released:
                print(f"  - {node_id}")


def cmd_orchestrator_enable(args: argparse.Namespace) -> None:
    """Enable orchestrator mode."""
    from typing import Literal

    from htmlgraph.orchestrator_mode import OrchestratorModeManager

    manager = OrchestratorModeManager(args.graph_dir)
    level: Literal["strict", "guidance"] = (
        args.level if hasattr(args, "level") and args.level else "strict"
    )
    manager.enable(level=level)

    level_text = "strict enforcement" if level == "strict" else "guidance mode"
    print(f"✓ Orchestrator mode enabled ({level_text})")


def cmd_orchestrator_disable(args: argparse.Namespace) -> None:
    """Disable orchestrator mode."""
    from htmlgraph.orchestrator_mode import OrchestratorModeManager

    manager = OrchestratorModeManager(args.graph_dir)
    manager.disable(by_user=True)
    print("✓ Orchestrator mode disabled")


def cmd_orchestrator_status(args: argparse.Namespace) -> None:
    """Show orchestrator mode status."""
    from htmlgraph.orchestrator_mode import OrchestratorModeManager

    manager = OrchestratorModeManager(args.graph_dir)
    status = manager.status()

    if status["enabled"]:
        level = status["enforcement_level"]
        level_text = "strict enforcement" if level == "strict" else "guidance mode"
        print(f"Orchestrator mode: enabled ({level_text})")
        if status["activated_at"]:
            print(f"Activated at: {status['activated_at']}")
        if status["auto_activated"]:
            print("Auto-activated: yes")

        # Show violation tracking info
        violations = status.get("violations", 0)
        circuit_breaker = status.get("circuit_breaker_triggered", False)
        if violations > 0:
            print(f"Violations: {violations}/3")
            if circuit_breaker:
                print("⚠️  Circuit breaker: TRIGGERED")
    else:
        print("Orchestrator mode: disabled")
        if status["disabled_by_user"]:
            print("Disabled by user (auto-activation prevented)")


def cmd_orchestrator_set_level(args: argparse.Namespace) -> None:
    """Set orchestrator mode enforcement level."""
    from typing import Literal

    from htmlgraph.orchestrator_mode import OrchestratorModeManager

    manager = OrchestratorModeManager(args.graph_dir)
    level: Literal["strict", "guidance"] = args.level
    manager.set_level(level)

    level_text = "strict enforcement" if level == "strict" else "guidance mode"
    print(f"✓ Orchestrator enforcement level set to: {level_text}")


def cmd_orchestrator_reset_violations(args: argparse.Namespace) -> None:
    """Reset orchestrator mode violation counter."""
    from htmlgraph.orchestrator_mode import OrchestratorModeManager

    manager = OrchestratorModeManager(args.graph_dir)

    # Check if mode is enabled
    if not manager.is_enabled():
        print("⚠️  Orchestrator mode is not enabled")
        return

    # Reset violations
    manager.reset_violations()

    print("✓ Violation counter reset")
    print("Circuit breaker: cleared")
    print("You can now continue with delegation workflow")


def cmd_publish(args: argparse.Namespace) -> None:
    """Build and publish the package to PyPI (Interoperable)."""
    import shutil
    import subprocess

    # Ensure we are in project root
    if not Path("pyproject.toml").exists():
        print(
            "Error: pyproject.toml not found. Run this from the project root.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 1. Clean dist/
    dist_dir = Path("dist")
    if dist_dir.exists():
        print("Cleaning dist/...")
        shutil.rmtree(dist_dir)

    # 2. Build
    print("Building package with uv...")
    try:
        subprocess.run(["uv", "build"], check=True)
    except subprocess.CalledProcessError:
        print("Error: Build failed.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'uv' command not found.", file=sys.stderr)
        sys.exit(1)

    # 3. Publish
    if args.dry_run:
        print("Dry run: Skipping publish.")
        return

    print("Publishing to PyPI...")
    env = os.environ.copy()

    # Smart credential loading from .env
    # Maps PyPI_API_TOKEN (common in .env) to UV_PUBLISH_TOKEN (needed by uv)
    if "UV_PUBLISH_TOKEN" not in env:
        dotenv = Path(".env")
        if dotenv.exists():
            try:
                content = dotenv.read_text()
                for line in content.splitlines():
                    if line.strip() and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key == "PyPI_API_TOKEN":
                            env["UV_PUBLISH_TOKEN"] = val
                            print("Loaded credentials from .env")
            except Exception:
                pass

    try:
        subprocess.run(["uv", "publish"], env=env, check=True)
        print("\n✅ Successfully published!")
    except subprocess.CalledProcessError:
        print("\n❌ Publish failed.", file=sys.stderr)
        sys.exit(1)


def cmd_feature_list(args: argparse.Namespace) -> None:
    """List features by status."""
    import json

    from htmlgraph.converter import node_to_dict
    from htmlgraph.sdk import SDK

    # Use SDK for feature queries
    sdk = SDK(directory=args.graph_dir)

    # Query features with SDK
    if args.status:
        nodes = sdk.features.where(status=args.status)
    else:
        nodes = sdk.features.all()

    # Sort by priority then updated
    from datetime import timezone

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def sort_key(n: Any) -> Any:
        # Ensure timezone-aware datetime for comparison
        updated = n.updated
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        return (priority_order.get(n.priority, 99), updated)

    nodes.sort(key=sort_key, reverse=True)

    if args.format == "json":
        response = create_json_response(
            command="feature list",
            data=[node_to_dict(n) for n in nodes],
            metadata={
                "graph_dir": args.graph_dir,
                "status_filter": args.status,
                "total_count": len(nodes),
            },
        )
        print(json.dumps(response, indent=2, default=str))
    else:
        if not nodes:
            if not args.quiet:
                print(
                    f"No features found with status '{args.status}'."
                    if args.status
                    else "No features found."
                )
            return

        # Header (skip if quiet)
        if not args.quiet:
            print(f"{'ID':<25} {'Status':<12} {'Priority':<10} {'Title'}")
            print("=" * 80)

        # List features
        for node in nodes:
            title = node.title[:35] + "..." if len(node.title) > 38 else node.title
            print(f"{node.id:<25} {node.status:<12} {node.priority:<10} {title}")

        # Verbose output
        if args.verbose >= 1:
            print("\n--- Verbose Details ---")
            print(f"Total features: {len(nodes)}")
            print(f"Graph directory: {args.graph_dir}")
            if args.status:
                print(f"Filtered by status: {args.status}")

        if args.verbose >= 2:
            print("\nFeature breakdown by status:")
            from collections import Counter

            status_counts = Counter(n.status for n in sdk.features.all())
            for status, count in sorted(status_counts.items()):
                marker = "→" if status == args.status else " "
                print(f"  {marker} {status}: {count}")


# =============================================================================
# Track Management Commands (Conductor-Style Planning)
# =============================================================================


def cmd_feature_step_complete(args: argparse.Namespace) -> None:
    """Mark one or more feature steps as complete via API."""
    import http.client
    import json

    # Parse step indices (support both space-separated and comma-separated)
    step_indices: list[int] = []
    for step_arg in args.steps:
        if "," in step_arg:
            # Comma-separated: "0,1,2"
            step_indices.extend(
                int(s.strip()) for s in step_arg.split(",") if s.strip()
            )
        else:
            # Space-separated: "0" "1" "2"
            step_indices.append(int(step_arg))

    # Remove duplicates and sort
    step_indices = sorted(set(step_indices))

    if not step_indices:
        print("Error: No step indices provided", file=sys.stderr)
        sys.exit(1)

    # Make API requests for each step
    success_count = 0
    error_count = 0
    results = []

    for step_index in step_indices:
        try:
            conn = http.client.HTTPConnection(args.host, args.port, timeout=5)
            body = json.dumps({"complete_step": step_index})
            headers = {"Content-Type": "application/json"}

            conn.request("PATCH", f"/api/{args.collection}/{args.id}", body, headers)
            response = conn.getresponse()
            response_data = response.read().decode()

            if response.status == 200:
                success_count += 1
                results.append({"step": step_index, "status": "success"})
                if args.format != "json":
                    print(f"✓ Marked step {step_index} complete")
            else:
                error_count += 1
                results.append(
                    {"step": step_index, "status": "error", "message": response_data}
                )
                if args.format != "json":
                    print(
                        f"✗ Failed to mark step {step_index} complete: {response_data}",
                        file=sys.stderr,
                    )

            conn.close()
        except Exception as e:
            error_count += 1
            results.append({"step": step_index, "status": "error", "message": str(e)})
            if args.format != "json":
                print(
                    f"✗ Error marking step {step_index} complete: {e}", file=sys.stderr
                )

    # Output results
    if args.format == "json":
        output = {
            "feature_id": args.id,
            "total_steps": len(step_indices),
            "success": success_count,
            "errors": error_count,
            "results": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(
            f"\nCompleted {success_count}/{len(step_indices)} steps for feature '{args.id}'"
        )
        if error_count > 0:
            sys.exit(1)


def cmd_feature_delete(args: argparse.Namespace) -> None:
    """Delete a feature."""
    import json
    import sys

    from htmlgraph import SDK

    sdk = SDK(agent=getattr(args, "agent", "cli"), directory=args.graph_dir)

    # Get the feature first to show confirmation
    collection = getattr(sdk, args.collection, None)
    if not collection:
        print(f"Error: Collection '{args.collection}' not found", file=sys.stderr)
        sys.exit(1)

    feature = collection.get(args.id)
    if not feature:
        print(
            f"Error: {args.collection.rstrip('s').capitalize()} '{args.id}' not found",
            file=sys.stderr,
        )
        sys.exit(1)

    # Confirmation prompt (unless --yes flag)
    if not args.yes:
        print(f"Delete {args.collection.rstrip('s')} '{args.id}'?")
        print(f"  Title: {feature.title}")
        print(f"  Status: {feature.status}")
        print("\nThis cannot be undone. Continue? [y/N] ", end="")

        response = input().strip().lower()
        if response not in ("y", "yes"):
            print("Cancelled")
            sys.exit(0)

    # Delete
    try:
        success = collection.delete(args.id)
        if success:
            if args.format == "json":
                data = {"id": args.id, "title": feature.title, "deleted": True}
                print(json.dumps(data, indent=2))
            else:
                print(f"Deleted {args.collection.rstrip('s')}: {args.id}")
                print(f"  Title: {feature.title}")
        else:
            print(
                f"Error: Failed to delete {args.collection.rstrip('s')} '{args.id}'",
                file=sys.stderr,
            )
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_track_new(args: argparse.Namespace) -> None:
    """Create a new track."""
    import json

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)

    try:
        track = manager.create_track(
            title=args.title,
            description=args.description or "",
            priority=args.priority,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": track.id,
            "title": track.title,
            "status": track.status,
            "priority": track.priority,
            "path": f"{args.graph_dir}/tracks/{track.id}/",
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created track: {track.id}")
        print(f"  Title: {track.title}")
        print(f"  Status: {track.status}")
        print(f"  Priority: {track.priority}")
        print(f"  Path: {args.graph_dir}/tracks/{track.id}/")
        print("\nNext steps:")
        print(f"  - Create spec: htmlgraph track spec {track.id} 'Spec Title'")
        print(f"  - Create plan: htmlgraph track plan {track.id} 'Plan Title'")


def cmd_track_list(args: argparse.Namespace) -> None:
    """List all tracks."""
    import json

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)
    track_ids = manager.list_tracks()

    if args.format == "json":
        print(json.dumps({"tracks": track_ids}, indent=2))
    else:
        if not track_ids:
            print("No tracks found.")
            print("\nCreate a track with: htmlgraph track new 'Track Title'")
            return

        print(f"Tracks in {args.graph_dir}/tracks/:")
        print("=" * 60)
        for track_id in track_ids:
            # Check for both consolidated (single file) and directory-based formats
            track_file = Path(args.graph_dir) / "tracks" / f"{track_id}.html"
            track_dir = Path(args.graph_dir) / "tracks" / track_id

            if track_file.exists():
                # Consolidated format - spec and plan are in the same file
                content = track_file.read_text(encoding="utf-8")
                has_spec = (
                    'data-section="overview"' in content
                    or 'data-section="requirements"' in content
                )
                has_plan = 'data-section="plan"' in content
                format_indicator = " (consolidated)"
            else:
                # Directory format
                has_spec = (track_dir / "spec.html").exists()
                has_plan = (track_dir / "plan.html").exists()
                format_indicator = ""

            components = []
            if has_spec:
                components.append("spec")
            if has_plan:
                components.append("plan")

            components_str = f" [{', '.join(components)}]" if components else " [empty]"
            print(f"  {track_id}{components_str}{format_indicator}")


def cmd_track_spec(args: argparse.Namespace) -> None:
    """Create a spec for a track."""
    import json

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)

    # Check if track uses consolidated format
    if manager.is_consolidated(args.track_id):
        track_file = manager.tracks_dir / f"{args.track_id}.html"
        print(f"Track '{args.track_id}' uses consolidated single-file format.")
        print(f"Spec is embedded in: {track_file}")
        print("\nTo create a track with separate spec/plan files, use:")
        print("  sdk.tracks.builder().separate_files().title('...').create()")
        return

    try:
        spec = manager.create_spec(
            track_id=args.track_id,
            title=args.title,
            overview=args.overview or "",
            context=args.context or "",
            author=args.author,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": spec.id,
            "title": spec.title,
            "track_id": spec.track_id,
            "status": spec.status,
            "path": f"{args.graph_dir}/tracks/{args.track_id}/spec.html",
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created spec: {spec.id}")
        print(f"  Title: {spec.title}")
        print(f"  Track: {spec.track_id}")
        print(f"  Status: {spec.status}")
        print(f"  Path: {args.graph_dir}/tracks/{args.track_id}/spec.html")
        print(f"\nView spec: open {args.graph_dir}/tracks/{args.track_id}/spec.html")


def cmd_track_plan(args: argparse.Namespace) -> None:
    """Create a plan for a track."""
    import json

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)

    # Check if track uses consolidated format
    if manager.is_consolidated(args.track_id):
        track_file = manager.tracks_dir / f"{args.track_id}.html"
        print(f"Track '{args.track_id}' uses consolidated single-file format.")
        print(f"Plan is embedded in: {track_file}")
        print("\nTo create a track with separate spec/plan files, use:")
        print("  sdk.tracks.builder().separate_files().title('...').create()")
        return

    try:
        plan = manager.create_plan(
            track_id=args.track_id,
            title=args.title,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": plan.id,
            "title": plan.title,
            "track_id": plan.track_id,
            "status": plan.status,
            "path": f"{args.graph_dir}/tracks/{args.track_id}/plan.html",
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Created plan: {plan.id}")
        print(f"  Title: {plan.title}")
        print(f"  Track: {plan.track_id}")
        print(f"  Status: {plan.status}")
        print(f"  Path: {args.graph_dir}/tracks/{args.track_id}/plan.html")
        print(f"\nView plan: open {args.graph_dir}/tracks/{args.track_id}/plan.html")


def cmd_track_show(args: argparse.Namespace) -> None:
    """Show details of a track."""
    import json
    from pathlib import Path

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)

    # Load the track
    track = manager.load_track(args.track_id)
    if not track:
        print(f"Error: Track '{args.track_id}' not found", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {
            "id": track.id,
            "title": track.title,
            "description": track.description,
            "status": track.status,
            "priority": track.priority,
            "has_spec": track.has_spec,
            "has_plan": track.has_plan,
            "created": track.created.isoformat(),
            "updated": track.updated.isoformat(),
            "features": track.features,
            "sessions": track.sessions,
        }
        print(json.dumps(data, indent=2))
    else:
        # Determine if consolidated or directory-based
        is_consolidated = manager.is_consolidated(args.track_id)
        if is_consolidated:
            track_file = Path(args.graph_dir) / "tracks" / f"{args.track_id}.html"
            file_type = "single file (consolidated)"
        else:
            track_file = Path(args.graph_dir) / "tracks" / args.track_id / "index.html"
            file_type = "directory-based"

        print(f"Track: {track.id}")
        print(f"  Title: {track.title}")
        print(f"  Description: {track.description}")
        print(f"  Status: {track.status}")
        print(f"  Priority: {track.priority}")
        print(f"  Format: {file_type}")
        print(f"  Has Spec: {'Yes' if track.has_spec else 'No'}")
        print(f"  Has Plan: {'Yes' if track.has_plan else 'No'}")
        print(f"  Created: {track.created.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Updated: {track.updated.strftime('%Y-%m-%d %H:%M')}")
        if track.features:
            print(f"  Features: {', '.join(track.features)}")
        if track.sessions:
            print(f"  Sessions: {', '.join(track.sessions)}")
        print(f"\nPath: {track_file}")
        print(f"View: open {track_file}")


def cmd_track_delete(args: argparse.Namespace) -> None:
    """Delete a track."""
    import json

    from htmlgraph.track_manager import TrackManager

    manager = TrackManager(args.graph_dir)

    try:
        manager.delete_track(args.track_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        data = {"deleted": True, "track_id": args.track_id}
        print(json.dumps(data, indent=2))
    else:
        print(f"✓ Deleted track: {args.track_id}")
        print(f"  Removed: {args.graph_dir}/tracks/{args.track_id}/")


def create_default_index(path: Path) -> None:
    """
    Create a default index.html for new projects.

    The dashboard UI evolves quickly; to keep new projects consistent with the
    current dashboard, prefer a packaged HTML template over a hardcoded string.
    """
    template = Path(__file__).parent / "dashboard.html"
    try:
        if template.exists():
            path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
            return
    except Exception:
        pass

    # Fallback (rare): minimal landing page.
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>HtmlGraph</title></head>"
        "<body><h1>HtmlGraph</h1><p>Run <code>htmlgraph serve</code> and open "
        "<code>http://localhost:8080</code>.</p></body></html>",
        encoding="utf-8",
    )


def cmd_claude(args: argparse.Namespace) -> None:
    """Start Claude Code with orchestrator prompt."""
    import textwrap

    # Load orchestration rules from plugin
    rules_file = (
        Path(__file__).parent.parent.parent.parent
        / "packages"
        / "claude-plugin"
        / "rules"
        / "orchestration.md"
    )

    orchestration_rules = ""
    if rules_file.exists():
        orchestration_rules = rules_file.read_text(encoding="utf-8")

    try:
        if args.init:
            # Load optimized orchestrator system prompt
            prompt_file = (
                Path(__file__).parent / "orchestrator-system-prompt-optimized.txt"
            )

            if prompt_file.exists():
                system_prompt = prompt_file.read_text(encoding="utf-8")
            else:
                # Fallback: provide minimal orchestrator guidance
                system_prompt = textwrap.dedent(
                    """
                    You are an AI orchestrator for HtmlGraph project development.

                    CRITICAL DIRECTIVES:
                    1. DELEGATE to subagents - do not implement directly
                    2. CREATE work items before delegating (features, bugs, spikes)
                    3. USE SDK for tracking - all work must be tracked in .htmlgraph/
                    4. RESPECT dependencies - check blockers before starting

                    Key Rules:
                    - Implementation work → delegate to general-purpose subagent
                    - Research/exploration → delegate to explorer subagent
                    - Testing/validation → delegate to test-runner subagent
                    - Complex analysis → delegate to appropriate specialist

                    Always use:
                        from htmlgraph import SDK
                        sdk = SDK(agent='orchestrator')

                    See CLAUDE.md for complete orchestrator directives.
                    """
                )

            # Combine fallback prompt with orchestration rules
            combined_prompt = system_prompt
            if orchestration_rules:
                combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"

            if args.quiet or args.format == "json":
                # Non-interactive: directly launch Claude with system prompt
                cmd = ["claude", "--append-system-prompt", combined_prompt]
            else:
                # Interactive: show summary first
                print("=" * 60)
                print("🤖 HtmlGraph Orchestrator Mode")
                print("=" * 60)
                print("\nStarting Claude Code with orchestrator system prompt...")
                print("Key directives:")
                print("  ✓ Delegate to Gemini (FREE), Codex, Copilot first")
                print("  ✓ Use Task() only as fallback")
                print("  ✓ Create work items before delegating")
                print("  ✓ Track all work in .htmlgraph/")
                print()

                cmd = ["claude", "--append-system-prompt", combined_prompt]

            try:
                subprocess.run(cmd, check=False)
            except FileNotFoundError:
                print("Error: 'claude' command not found.", file=sys.stderr)
                print(
                    "Please install Claude Code CLI: https://code.claude.com",
                    file=sys.stderr,
                )
                sys.exit(1)

        elif args.continue_session:
            # Resume last Claude Code session
            # Find plugin directory relative to project root
            plugin_dir = (
                Path(__file__).parent.parent.parent.parent
                / "packages"
                / "claude-plugin"
                / ".claude-plugin"
            )

            if args.quiet or args.format == "json":
                cmd = ["claude", "--resume"]
            else:
                print("Resuming last Claude Code session...")
                cmd = ["claude", "--resume"]

            # Add orchestration rules if available
            if orchestration_rules:
                cmd.extend(["--append-system-prompt", orchestration_rules])
                if not (args.quiet or args.format == "json"):
                    print("  ✓ Multi-AI delegation rules injected")

            # Add plugin directory if it exists
            if plugin_dir.exists():
                cmd.extend(["--plugin-dir", str(plugin_dir)])
                if not (args.quiet or args.format == "json"):
                    print(f"  ✓ Loading plugin from: {plugin_dir}")

            try:
                subprocess.run(cmd, check=False)
            except FileNotFoundError:
                print("Error: 'claude' command not found.", file=sys.stderr)
                print(
                    "Please install Claude Code CLI: https://code.claude.com",
                    file=sys.stderr,
                )
                sys.exit(1)

        elif args.dev:
            # Development mode: load plugin from local directory
            plugin_dir = (
                Path(__file__).parent.parent.parent.parent
                / "packages"
                / "claude-plugin"
                / ".claude-plugin"
            )

            if not plugin_dir.exists():
                print(
                    f"Error: Plugin directory not found: {plugin_dir}", file=sys.stderr
                )
                print(
                    "Expected location: packages/claude-plugin/.claude-plugin",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Load optimized orchestrator system prompt
            prompt_file = (
                Path(__file__).parent / "orchestrator-system-prompt-optimized.txt"
            )

            if prompt_file.exists():
                system_prompt = prompt_file.read_text(encoding="utf-8")
            else:
                # Fallback: provide minimal orchestrator guidance
                system_prompt = textwrap.dedent(
                    """
                    You are an AI orchestrator for HtmlGraph project development.

                    CRITICAL DIRECTIVES:
                    1. DELEGATE to subagents - do not implement directly
                    2. CREATE work items before delegating (features, bugs, spikes)
                    3. USE SDK for tracking - all work must be tracked in .htmlgraph/
                    4. RESPECT dependencies - check blockers before starting

                    Key Rules:
                    - Implementation work → delegate to general-purpose subagent
                    - Research/exploration → delegate to explorer subagent
                    - Testing/validation → delegate to test-runner subagent
                    - Complex analysis → delegate to appropriate specialist

                    Always use:
                        from htmlgraph import SDK
                        sdk = SDK(agent='orchestrator')

                    See CLAUDE.md for complete orchestrator directives.
                    """
                )

            # Combine orchestrator prompt with orchestration rules
            combined_prompt = system_prompt
            if orchestration_rules:
                combined_prompt = f"{system_prompt}\n\n---\n\n{orchestration_rules}"

            if args.quiet or args.format == "json":
                cmd = [
                    "claude",
                    "--plugin-dir",
                    str(plugin_dir),
                    "--append-system-prompt",
                    combined_prompt,
                ]
            else:
                print("=" * 60)
                print("🔧 HtmlGraph Development Mode")
                print("=" * 60)
                print(f"\nLoading plugin from: {plugin_dir}")
                print("  ✓ Skills, agents, and hooks will be loaded from local files")
                print("  ✓ Orchestrator system prompt will be appended")
                print("  ✓ Multi-AI delegation rules will be injected")
                print("  ✓ Changes to plugin files will take effect after restart")
                print()
                cmd = [
                    "claude",
                    "--plugin-dir",
                    str(plugin_dir),
                    "--append-system-prompt",
                    combined_prompt,
                ]

            try:
                subprocess.run(cmd, check=False)
            except FileNotFoundError:
                print("Error: 'claude' command not found.", file=sys.stderr)
                print(
                    "Please install Claude Code CLI: https://code.claude.com",
                    file=sys.stderr,
                )
                sys.exit(1)

        else:
            # Default: start normal Claude Code session
            cmd = ["claude"]

            # Add orchestration rules if available
            if orchestration_rules:
                cmd.extend(["--append-system-prompt", orchestration_rules])
                if not (args.quiet or args.format == "json"):
                    print("Starting Claude Code with multi-AI delegation rules...")

            try:
                subprocess.run(cmd, check=False)
            except FileNotFoundError:
                print("Error: 'claude' command not found.", file=sys.stderr)
                print(
                    "Please install Claude Code CLI: https://code.claude.com",
                    file=sys.stderr,
                )
                sys.exit(1)

    except Exception as e:
        print(f"Error: Failed to start Claude Code: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HtmlGraph - HTML is All You Need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  htmlgraph init                    # Initialize .htmlgraph in current dir
  htmlgraph serve                   # Start server on port 8080
  htmlgraph status                  # Show graph status
  htmlgraph query "[data-status='todo']"  # Query nodes

Session Management:
  htmlgraph session start           # Start a new session (auto-ID)
  htmlgraph session start --id my-session --title "Bug fixes"
  htmlgraph session end my-session  # End a session
  htmlgraph session list            # List all sessions
  htmlgraph activity Edit "Edit: src/app.py:45-60" --files src/app.py

Feature Management:
  htmlgraph feature list            # List all features
  htmlgraph feature start feat-001  # Start working on a feature
  htmlgraph feature primary feat-001  # Set primary feature
  htmlgraph feature claim feat-001  # Claim feature for current agent
  htmlgraph feature release feat-001  # Release claim
  htmlgraph feature auto-release    # Release all claims for agent
  htmlgraph feature step-complete feat-001 0 1 2  # Mark steps complete
  htmlgraph feature complete feat-001  # Mark feature as done

Track Management (Conductor-Style Planning):
  htmlgraph track new "User Authentication"  # Create a new track
  htmlgraph track list              # List all tracks
  htmlgraph track spec track-001-auth "Auth Specification"  # Create spec
  htmlgraph track plan track-001-auth "Auth Implementation Plan"  # Create plan

Analytics:
  htmlgraph analytics               # Project-wide work type analytics
  htmlgraph analytics --recent 10   # Analyze last 10 sessions
  htmlgraph analytics --session-id session-123  # Detailed session metrics

curl Examples:
  curl localhost:8080/api/status
  curl localhost:8080/api/features
  curl -X POST localhost:8080/api/features -d '{"title": "New feature"}'
  curl -X PATCH localhost:8080/api/features/feat-001 -d '{"status": "done"}'

Debugging & Quality:
  See DEBUGGING.md for comprehensive debugging guide

  Debugging agents:
    researcher.md  - Research documentation before implementing
    debugger.md    - Systematic error analysis
    test-runner.md - Quality gates and validation

  Quick diagnostics:
    htmlgraph status          - Check current state
    htmlgraph feature list    - List all features
    htmlgraph debug           - Show debugging resources

For more help: https://github.com/Shakes-tzd/htmlgraph
""",
    )

    # Global output control flags (work across all commands)
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress messages and non-essential output",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times: -v, -vv, -vvv)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the HtmlGraph server")
    serve_parser.add_argument(
        "--port", "-p", type=int, default=8080, help="Port (default: 8080)"
    )
    serve_parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    serve_parser.add_argument(
        "--static-dir", "-s", default=".", help="Static files directory"
    )
    serve_parser.add_argument(
        "--no-watch",
        action="store_true",
        help="Disable file watching (auto-reload disabled)",
    )
    serve_parser.add_argument(
        "--auto-port",
        action="store_true",
        help="Automatically find an available port if default is occupied",
    )

    # init
    init_parser = subparsers.add_parser("init", help="Initialize .htmlgraph directory")
    init_parser.add_argument(
        "dir", nargs="?", default=".", help="Directory to initialize"
    )
    init_parser.add_argument(
        "--install-hooks",
        action="store_true",
        help="Install Git hooks for event logging",
    )
    init_parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive setup wizard"
    )
    init_parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not create the analytics cache (index.sqlite)",
    )
    init_parser.add_argument(
        "--no-update-gitignore",
        action="store_true",
        help="Do not update/create .gitignore for HtmlGraph cache files",
    )
    init_parser.add_argument(
        "--no-events-keep",
        action="store_true",
        help="Do not create .htmlgraph/events/.gitkeep",
    )

    # install-hooks
    hooks_parser = subparsers.add_parser(
        "install-hooks", help="Install Git hooks for automatic tracking"
    )
    hooks_parser.add_argument(
        "--project-dir", "-d", default=".", help="Project directory (default: current)"
    )
    hooks_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force installation even if hooks exist",
    )
    hooks_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    hooks_parser.add_argument(
        "--list", "-l", action="store_true", help="List hook installation status"
    )
    hooks_parser.add_argument(
        "--uninstall", "-u", metavar="HOOK", help="Uninstall a specific hook"
    )
    hooks_parser.add_argument(
        "--enable", metavar="HOOK", help="Enable a specific hook in configuration"
    )
    hooks_parser.add_argument(
        "--disable", metavar="HOOK", help="Disable a specific hook in configuration"
    )
    hooks_parser.add_argument(
        "--use-copy", action="store_true", help="Use file copy instead of symlinks"
    )

    # status
    status_parser = subparsers.add_parser("status", help="Show graph status")
    status_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # debug
    debug_parser = subparsers.add_parser(
        "debug", help="Show debugging resources and system diagnostics"
    )
    debug_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # query
    query_parser = subparsers.add_parser("query", help="Query nodes with CSS selector")
    query_parser.add_argument(
        "selector", help="CSS selector (e.g. [data-status='todo'])"
    )
    query_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    query_parser.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Session Management
    # =========================================================================

    # session (with subcommands)
    session_parser = subparsers.add_parser("session", help="Session management")
    session_subparsers = session_parser.add_subparsers(
        dest="session_command", help="Session command"
    )

    # session start
    session_start = session_subparsers.add_parser("start", help="Start a new session")
    session_start.add_argument(
        "--id", help="Session ID (auto-generated if not provided)"
    )
    session_start.add_argument("--agent", default="claude-code", help="Agent name")
    session_start.add_argument("--title", help="Session title")
    session_start.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_start.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # session end
    session_end = session_subparsers.add_parser("end", help="End a session")
    session_end.add_argument("id", help="Session ID to end")
    session_end.add_argument("--notes", help="Handoff notes for the next session")
    session_end.add_argument("--recommend", help="Recommended next steps")
    session_end.add_argument(
        "--blocker", action="append", default=[], help="Blocker to record (repeatable)"
    )
    session_end.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_end.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # session handoff
    session_handoff = session_subparsers.add_parser(
        "handoff", help="Set or show session handoff context"
    )
    session_handoff.add_argument(
        "--session-id", help="Session ID (defaults to active session)"
    )
    session_handoff.add_argument(
        "--agent", help="Agent filter (used for --show when no session provided)"
    )
    session_handoff.add_argument("--notes", help="Handoff notes for the next session")
    session_handoff.add_argument("--recommend", help="Recommended next steps")
    session_handoff.add_argument(
        "--blocker", action="append", default=[], help="Blocker to record (repeatable)"
    )
    session_handoff.add_argument(
        "--show", action="store_true", help="Show handoff context instead of setting it"
    )
    session_handoff.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_handoff.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # session list
    session_list = session_subparsers.add_parser("list", help="List all sessions")
    session_list.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_list.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # session start-info (optimized for AI agents)
    session_start_info = session_subparsers.add_parser(
        "start-info", help="Get comprehensive session start information (optimized)"
    )
    session_start_info.add_argument("--agent", default="claude", help="Agent name")
    session_start_info.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_start_info.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )
    session_start_info.add_argument(
        "--no-git", action="store_true", help="Skip git log"
    )
    session_start_info.add_argument(
        "--git-count", type=int, default=5, help="Number of git commits to include"
    )
    session_start_info.add_argument(
        "--top-n", type=int, default=3, help="Number of bottlenecks/recommendations"
    )
    session_start_info.add_argument(
        "--max-agents",
        type=int,
        default=3,
        help="Max agents for parallel work analysis",
    )

    # session status-report (and resume alias)
    session_report = session_subparsers.add_parser(
        "status-report", help="Print comprehensive session status report"
    )
    session_report.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    session_resume = session_subparsers.add_parser(
        "resume", help="Alias for status-report (Resume session context)"
    )
    session_resume.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # session dedupe
    session_dedupe = session_subparsers.add_parser(
        "dedupe",
        help="Move SessionStart-only sessions into a subfolder",
    )
    session_dedupe.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_dedupe.add_argument(
        "--max-events", type=int, default=1, help="Max events to consider orphaned"
    )
    session_dedupe.add_argument(
        "--move-dir", default="_orphans", help="Subfolder name under sessions/"
    )
    session_dedupe.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without moving files",
    )
    session_dedupe.add_argument(
        "--no-stale-active",
        action="store_true",
        help="Do not mark extra active sessions as stale",
    )

    # session link
    session_link = session_subparsers.add_parser(
        "link", help="Link a feature to a session retroactively"
    )
    session_link.add_argument("session_id", help="Session ID")
    session_link.add_argument("feature_id", help="Feature ID to link")
    session_link.add_argument(
        "--collection", "-c", default="features", help="Feature collection"
    )
    session_link.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_link.add_argument(
        "--bidirectional",
        "-b",
        action="store_true",
        help="Also add session to feature's implemented-in edges",
    )
    session_link.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # session validate-attribution
    session_validate = session_subparsers.add_parser(
        "validate-attribution", help="Validate feature attribution and tracking"
    )
    session_validate.add_argument("feature_id", help="Feature ID to validate")
    session_validate.add_argument(
        "--collection", "-c", default="features", help="Feature collection"
    )
    session_validate.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    session_validate.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # activity (legacy: was "track")
    activity_parser = subparsers.add_parser(
        "activity",
        help="Track an activity (legacy: use 'htmlgraph track' for new features)",
    )
    activity_parser.add_argument("tool", help="Tool name (Edit, Bash, Read, etc.)")
    activity_parser.add_argument("summary", help="Activity summary")
    activity_parser.add_argument(
        "--session", help="Session ID (uses active session if not provided)"
    )
    activity_parser.add_argument("--files", nargs="*", help="Files involved")
    activity_parser.add_argument("--failed", action="store_true", help="Mark as failed")
    activity_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    activity_parser.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Transcript Management (Claude Code Integration)
    # =========================================================================

    transcript_parser = subparsers.add_parser(
        "transcript", help="Claude Code transcript integration"
    )
    transcript_subparsers = transcript_parser.add_subparsers(
        dest="transcript_command", help="Transcript command"
    )

    # transcript list
    transcript_list = transcript_subparsers.add_parser(
        "list", help="List available Claude Code transcripts"
    )
    transcript_list.add_argument("--project", "-p", help="Project path to filter by")
    transcript_list.add_argument(
        "--limit", "-n", type=int, default=20, help="Maximum transcripts to show"
    )
    transcript_list.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript import
    transcript_import = transcript_subparsers.add_parser(
        "import", help="Import a Claude Code transcript"
    )
    transcript_import.add_argument(
        "session_id", help="Claude Code session ID to import"
    )
    transcript_import.add_argument(
        "--to-session",
        help="HtmlGraph session ID to import into (creates new if not specified)",
    )
    transcript_import.add_argument("--link-feature", help="Feature ID to link to")
    transcript_import.add_argument(
        "--agent", default="claude-code", help="Agent name for new session"
    )
    transcript_import.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing activities"
    )
    transcript_import.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_import.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript link
    transcript_link = transcript_subparsers.add_parser(
        "link", help="Link a transcript to an HtmlGraph session"
    )
    transcript_link.add_argument("session_id", help="Claude Code session ID")
    transcript_link.add_argument(
        "--to-session", required=True, help="HtmlGraph session ID to link to"
    )
    transcript_link.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_link.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript stats
    transcript_stats = transcript_subparsers.add_parser(
        "stats", help="Show transcript statistics for a session"
    )
    transcript_stats.add_argument("session_id", help="HtmlGraph session ID")
    transcript_stats.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_stats.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript auto-link
    transcript_auto_link = transcript_subparsers.add_parser(
        "auto-link", help="Auto-link transcripts by git branch"
    )
    transcript_auto_link.add_argument(
        "--branch", "-b", help="Git branch (uses current if not specified)"
    )
    transcript_auto_link.add_argument("--agent", help="Filter by agent")
    transcript_auto_link.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_auto_link.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript health (analytics)
    transcript_health = transcript_subparsers.add_parser(
        "health", help="Show session health metrics from transcript"
    )
    transcript_health.add_argument(
        "transcript_id", help="Transcript/session ID to analyze"
    )
    transcript_health.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_health.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript patterns (analytics)
    transcript_patterns = transcript_subparsers.add_parser(
        "patterns", help="Detect workflow patterns in transcripts"
    )
    transcript_patterns.add_argument(
        "--transcript-id", "-t", help="Specific transcript to analyze (default: all)"
    )
    transcript_patterns.add_argument(
        "--min-length", type=int, default=3, help="Minimum pattern length (default: 3)"
    )
    transcript_patterns.add_argument(
        "--max-length", type=int, default=5, help="Maximum pattern length (default: 5)"
    )
    transcript_patterns.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_patterns.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript transitions (analytics)
    transcript_transitions = transcript_subparsers.add_parser(
        "transitions", help="Show tool transition matrix"
    )
    transcript_transitions.add_argument(
        "--transcript-id", "-t", help="Specific transcript to analyze (default: all)"
    )
    transcript_transitions.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_transitions.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript recommendations (analytics)
    transcript_recs = transcript_subparsers.add_parser(
        "recommendations", help="Get workflow improvement recommendations"
    )
    transcript_recs.add_argument(
        "--transcript-id", "-t", help="Specific transcript to analyze (default: all)"
    )
    transcript_recs.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_recs.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript insights (analytics)
    transcript_insights = transcript_subparsers.add_parser(
        "insights", help="Get comprehensive transcript insights"
    )
    transcript_insights.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_insights.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript export (HTML export)
    transcript_export = transcript_subparsers.add_parser(
        "export", help="Export transcript to HTML format"
    )
    transcript_export.add_argument(
        "transcript_id", help="Transcript/session ID to export"
    )
    transcript_export.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if not specified)"
    )
    transcript_export.add_argument(
        "--include-thinking",
        action="store_true",
        help="Include thinking traces in output",
    )

    # transcript track-stats (track-level aggregation)
    transcript_track = transcript_subparsers.add_parser(
        "track-stats", help="Get aggregated transcript stats for a track"
    )
    transcript_track.add_argument("track_id", help="Track ID to aggregate")
    transcript_track.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_track.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # transcript link-feature (link transcript to feature for parallel agent tracking)
    transcript_link_feature = transcript_subparsers.add_parser(
        "link-feature",
        help="Link a Claude Code transcript to a feature (for parallel agent tracking)",
    )
    transcript_link_feature.add_argument(
        "transcript_id", help="Claude Code transcript/agent session ID"
    )
    transcript_link_feature.add_argument(
        "--to-feature", "-f", required=True, help="Feature ID to link to"
    )
    transcript_link_feature.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    transcript_link_feature.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Work Management (Smart Routing)
    # =========================================================================

    # work (with subcommands)
    work_parser = subparsers.add_parser(
        "work", help="Work management with smart routing"
    )
    work_subparsers = work_parser.add_subparsers(
        dest="work_command", help="Work command"
    )

    # work next
    work_next = work_subparsers.add_parser(
        "next", help="Get next best task using smart routing"
    )
    work_next.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "claude",
        help="Agent ID (default: $HTMLGRAPH_AGENT or 'claude')",
    )
    work_next.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    work_next.add_argument(
        "--auto-claim", action="store_true", help="Automatically claim the task"
    )
    work_next.add_argument(
        "--min-score",
        type=float,
        default=20.0,
        help="Minimum routing score (default: 20.0)",
    )
    work_next.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # work queue
    work_queue = work_subparsers.add_parser("queue", help="Get prioritized work queue")
    work_queue.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "claude",
        help="Agent ID (default: $HTMLGRAPH_AGENT or 'claude')",
    )
    work_queue.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    work_queue.add_argument(
        "--limit",
        "-l",
        type=int,
        default=10,
        help="Maximum tasks to show (default: 10)",
    )
    work_queue.add_argument(
        "--min-score",
        type=float,
        default=20.0,
        help="Minimum routing score (default: 20.0)",
    )
    work_queue.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # agent (with subcommands)
    agent_parser = subparsers.add_parser("agent", help="Agent management")
    agent_subparsers = agent_parser.add_subparsers(
        dest="agent_command", help="Agent command"
    )

    # agent list
    agent_list = agent_subparsers.add_parser("list", help="List all registered agents")
    agent_list.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    agent_list.add_argument(
        "--active-only", action="store_true", help="Only show active agents"
    )
    agent_list.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Feature Management
    # =========================================================================

    # feature (with subcommands)
    feature_parser = subparsers.add_parser("feature", help="Feature management")
    feature_subparsers = feature_parser.add_subparsers(
        dest="feature_command", help="Feature command"
    )

    # feature create
    feature_create = feature_subparsers.add_parser(
        "create", help="Create a new feature"
    )
    feature_create.add_argument("title", help="Feature title")
    feature_create.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_create.add_argument("--description", "-d", help="Description")
    feature_create.add_argument(
        "--priority",
        "-p",
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Priority",
    )
    feature_create.add_argument("--steps", nargs="*", help="Implementation steps")
    feature_create.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_create.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_create.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature start
    feature_start = feature_subparsers.add_parser(
        "start", help="Start working on a feature"
    )
    feature_start.add_argument("id", help="Feature ID")
    feature_start.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_start.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_start.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_start.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature complete
    feature_complete = feature_subparsers.add_parser(
        "complete", help="Mark feature as complete"
    )
    feature_complete.add_argument("id", help="Feature ID")
    feature_complete.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_complete.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_complete.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_complete.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature primary
    feature_primary = feature_subparsers.add_parser(
        "primary", help="Set primary feature"
    )
    feature_primary.add_argument("id", help="Feature ID")
    feature_primary.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_primary.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_primary.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_primary.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature claim
    feature_claim = feature_subparsers.add_parser("claim", help="Claim a feature")
    feature_claim.add_argument("id", help="Feature ID")
    feature_claim.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_claim.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_claim.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_claim.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature release
    feature_release = feature_subparsers.add_parser(
        "release", help="Release a feature claim"
    )
    feature_release.add_argument("id", help="Feature ID")
    feature_release.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_release.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_release.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_release.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature auto-release
    feature_auto_release = feature_subparsers.add_parser(
        "auto-release", help="Release all features claimed by agent"
    )
    feature_auto_release.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_auto_release.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_auto_release.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # feature list
    feature_list = feature_subparsers.add_parser("list", help="List features")
    feature_list.add_argument("--status", "-s", help="Filter by status")
    feature_list.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_list.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    # Note: --format flag is inherited from global parser (line 3312)

    # feature step-complete
    feature_step_complete = feature_subparsers.add_parser(
        "step-complete", help="Mark feature step(s) as complete"
    )
    feature_step_complete.add_argument("id", help="Feature ID")
    feature_step_complete.add_argument(
        "steps",
        nargs="+",
        help="Step index(es) to mark complete (0-based, supports: 0 1 2 or 0,1,2)",
    )
    feature_step_complete.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_step_complete.add_argument(
        "--agent",
        default=os.environ.get("HTMLGRAPH_AGENT") or "cli",
        help="Agent name for attribution (default: $HTMLGRAPH_AGENT or 'cli')",
    )
    feature_step_complete.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_step_complete.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )
    feature_step_complete.add_argument(
        "--host", default="localhost", help="API host (default: localhost)"
    )
    feature_step_complete.add_argument(
        "--port", type=int, default=8080, help="API port (default: 8080)"
    )

    # feature delete
    feature_delete = feature_subparsers.add_parser("delete", help="Delete a feature")
    feature_delete.add_argument("id", help="Feature ID to delete")
    feature_delete.add_argument(
        "--collection", "-c", default="features", help="Collection (features, bugs)"
    )
    feature_delete.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )
    feature_delete.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    feature_delete.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Track Management (Conductor-Style Planning)
    # =========================================================================

    # track (with subcommands)
    track_parser = subparsers.add_parser(
        "track", help="Track management (Conductor-style planning)"
    )
    track_subparsers = track_parser.add_subparsers(
        dest="track_command", help="Track command"
    )

    # track new
    track_new = track_subparsers.add_parser("new", help="Create a new track")
    track_new.add_argument("title", help="Track title")
    track_new.add_argument("--description", "-d", help="Track description")
    track_new.add_argument(
        "--priority",
        "-p",
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Priority",
    )
    track_new.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_new.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # track list
    track_list = track_subparsers.add_parser("list", help="List all tracks")
    track_list.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_list.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # track spec
    track_spec = track_subparsers.add_parser("spec", help="Create a spec for a track")
    track_spec.add_argument("track_id", help="Track ID")
    track_spec.add_argument("title", help="Spec title")
    track_spec.add_argument("--overview", "-o", help="Spec overview")
    track_spec.add_argument("--context", "-c", help="Context/rationale")
    track_spec.add_argument("--author", "-a", default="claude-code", help="Spec author")
    track_spec.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_spec.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # track plan
    track_plan = track_subparsers.add_parser("plan", help="Create a plan for a track")
    track_plan.add_argument("track_id", help="Track ID")
    track_plan.add_argument("title", help="Plan title")
    track_plan.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_plan.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # track show
    track_show = track_subparsers.add_parser("show", help="Show track details")
    track_show.add_argument("track_id", help="Track ID to display")
    track_show.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_show.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # track delete
    track_delete = track_subparsers.add_parser("delete", help="Delete a track")
    track_delete.add_argument("track_id", help="Track ID to delete")
    track_delete.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    track_delete.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Archive Management
    # =========================================================================

    # archive (with subcommands)
    archive_parser = subparsers.add_parser(
        "archive", help="Archive management with optimized search"
    )
    archive_subparsers = archive_parser.add_subparsers(
        dest="archive_command", help="Archive command"
    )

    # archive create
    archive_create = archive_subparsers.add_parser(
        "create", help="Create archive from old entities"
    )
    archive_create.add_argument(
        "--older-than",
        type=int,
        default=90,
        help="Archive entities older than N days (default: 90)",
    )
    archive_create.add_argument(
        "--period",
        choices=["quarter", "month", "year"],
        default="quarter",
        help="Archive grouping period (default: quarter)",
    )
    archive_create.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be archived without making changes",
    )
    archive_create.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # archive search
    archive_search = archive_subparsers.add_parser(
        "search", help="Search archived entities"
    )
    archive_search.add_argument("query", help="Search query")
    archive_search.add_argument(
        "--limit", "-l", type=int, default=10, help="Maximum results (default: 10)"
    )
    archive_search.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    archive_search.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # archive stats
    archive_stats = archive_subparsers.add_parser(
        "stats", help="Show archive statistics"
    )
    archive_stats.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    archive_stats.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # archive restore
    archive_restore = archive_subparsers.add_parser(
        "restore", help="Restore archived entity"
    )
    archive_restore.add_argument("entity_id", help="Entity ID to restore")
    archive_restore.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # archive list
    archive_list = archive_subparsers.add_parser("list", help="List all archive files")
    archive_list.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    archive_list.add_argument(
        "--format", "-f", choices=["text", "json"], default="text", help="Output format"
    )

    # =========================================================================
    # Analytics
    # =========================================================================

    # analytics
    analytics_parser = subparsers.add_parser(
        "analytics", help="Work type analytics and project health metrics"
    )
    analytics_parser.add_argument(
        "--session-id", "-s", help="Analyze specific session ID"
    )
    analytics_parser.add_argument(
        "--recent", "-r", type=int, help="Analyze N recent sessions"
    )
    analytics_parser.add_argument(
        "--agent", default="cli", help="Agent name for SDK initialization"
    )
    analytics_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # =========================================================================
    # Documentation Version Management
    # =========================================================================

    docs_parser = subparsers.add_parser("docs", help="Documentation version management")
    docs_subparsers = docs_parser.add_subparsers(
        dest="docs_command", help="Docs command"
    )

    docs_version = docs_subparsers.add_parser(
        "version", help="Check documentation version compatibility"
    )
    docs_version.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    docs_upgrade = docs_subparsers.add_parser(
        "upgrade", help="Upgrade documentation to latest version"
    )
    docs_upgrade.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    docs_upgrade.add_argument(
        "--auto", action="store_true", help="Auto-migrate without prompts"
    )

    docs_diff = docs_subparsers.add_parser("diff", help="Show migration diff preview")
    docs_diff.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    docs_rollback = docs_subparsers.add_parser(
        "rollback", help="Rollback to previous version"
    )
    docs_rollback.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    docs_rollback.add_argument(
        "version", nargs="?", help="Version to rollback to (default: latest backup)"
    )

    docs_generate = docs_subparsers.add_parser(
        "generate", help="Generate documentation from templates"
    )
    docs_generate.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    docs_generate.add_argument(
        "--platform",
        "-p",
        default="claude",
        choices=["claude", "gemini", "api", "cli"],
        help="Platform to generate docs for",
    )
    docs_generate.add_argument(
        "--output", "-o", help="Output file (default: AGENTS.md)"
    )

    # =========================================================================
    # Events & Analytics Index
    # =========================================================================

    events_parser = subparsers.add_parser("events", help="Event log utilities")
    events_subparsers = events_parser.add_subparsers(
        dest="events_command", help="Events command"
    )

    events_export = events_subparsers.add_parser(
        "export-sessions",
        help="Export session HTML activity logs to JSONL under .htmlgraph/events/",
    )
    events_export.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    events_export.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing JSONL files"
    )
    events_export.add_argument(
        "--include-subdirs",
        action="store_true",
        help="Include subdirectories like sessions/_orphans/",
    )

    index_parser = subparsers.add_parser("index", help="Analytics index commands")
    index_subparsers = index_parser.add_subparsers(
        dest="index_command", help="Index command"
    )

    index_rebuild = index_subparsers.add_parser(
        "rebuild",
        help="Rebuild .htmlgraph/index.sqlite from .htmlgraph/events/*.jsonl",
    )
    index_rebuild.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # watch
    watch_parser = subparsers.add_parser(
        "watch", help="Watch file changes and log events"
    )
    watch_parser.add_argument(
        "--root", "-r", default=".", help="Root directory to watch"
    )
    watch_parser.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    watch_parser.add_argument(
        "--session-id", help="Session ID (defaults to deduped active session)"
    )
    watch_parser.add_argument(
        "--agent", default="codex", help="Agent name for the watcher"
    )
    watch_parser.add_argument(
        "--interval", type=float, default=2.0, help="Polling interval seconds"
    )
    watch_parser.add_argument(
        "--batch-seconds", type=float, default=5.0, help="Batch window seconds"
    )

    # git-event
    git_event_parser = subparsers.add_parser(
        "git-event", help="Log Git events (commit, checkout, merge, push)"
    )
    git_event_parser.add_argument(
        "event_type",
        choices=["commit", "checkout", "merge", "push"],
        help="Type of Git event",
    )
    git_event_parser.add_argument(
        "args",
        nargs="*",
        help="Event-specific args (checkout: old new flag; merge: squash_flag; push: remote_name remote_url)",
    )

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="Minimal MCP server (stdio)")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", help="MCP command")
    mcp_serve = mcp_subparsers.add_parser("serve", help="Serve MCP over stdio")
    mcp_serve.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )
    mcp_serve.add_argument(
        "--agent", default="mcp", help="Agent name for session attribution"
    )

    # setup
    setup_parser = subparsers.add_parser(
        "setup", help="Set up HtmlGraph for AI CLI platforms"
    )
    setup_subparsers = setup_parser.add_subparsers(
        dest="setup_command", help="Platform to set up"
    )

    setup_claude = setup_subparsers.add_parser("claude", help="Set up for Claude Code")
    setup_claude.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install when possible",
    )

    setup_codex = setup_subparsers.add_parser("codex", help="Set up for Codex CLI")
    setup_codex.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install when possible",
    )

    setup_gemini = setup_subparsers.add_parser("gemini", help="Set up for Gemini CLI")
    setup_gemini.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install when possible",
    )

    setup_all_parser = setup_subparsers.add_parser(
        "all", help="Set up for all supported platforms"
    )
    setup_all_parser.add_argument(
        "--auto-install",
        action="store_true",
        help="Automatically install when possible",
    )

    # publish
    publish_parser = subparsers.add_parser(
        "publish", help="Build and publish package to PyPI"
    )
    publish_parser.add_argument(
        "--dry-run", action="store_true", help="Build only, do not publish"
    )

    # sync-docs
    sync_docs_parser = subparsers.add_parser(
        "sync-docs", help="Synchronize AI agent memory files across platforms"
    )
    sync_docs_parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are synchronized (no changes)",
    )
    sync_docs_parser.add_argument(
        "--generate",
        metavar="PLATFORM",
        help="Generate a platform-specific file (gemini, claude, codex)",
    )
    sync_docs_parser.add_argument(
        "--project-root",
        type=str,
        help="Project root directory (default: current directory)",
    )
    sync_docs_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing files when generating"
    )

    # deploy
    deploy_parser = subparsers.add_parser(
        "deploy", help="Flexible deployment system for packaging and publishing"
    )
    deploy_subparsers = deploy_parser.add_subparsers(
        dest="deploy_command", help="Deploy command"
    )

    # deploy init
    deploy_init = deploy_subparsers.add_parser(
        "init", help="Initialize deployment configuration"
    )
    deploy_init.add_argument(
        "--output", "-o", help="Output file path (default: htmlgraph-deploy.toml)"
    )
    deploy_init.add_argument(
        "--force", action="store_true", help="Overwrite existing configuration"
    )

    # deploy run
    deploy_run = deploy_subparsers.add_parser("run", help="Run deployment process")
    deploy_run.add_argument(
        "--config", "-c", help="Configuration file (default: htmlgraph-deploy.toml)"
    )
    deploy_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )
    deploy_run.add_argument(
        "--docs-only", action="store_true", help="Only commit and push to git"
    )
    deploy_run.add_argument(
        "--build-only", action="store_true", help="Only build package"
    )
    deploy_run.add_argument(
        "--skip-pypi", action="store_true", help="Skip PyPI publishing"
    )
    deploy_run.add_argument(
        "--skip-plugins", action="store_true", help="Skip plugin updates"
    )

    # orchestrator (with subcommands)
    orchestrator_parser = subparsers.add_parser(
        "orchestrator", help="Orchestrator mode management"
    )
    orchestrator_subparsers = orchestrator_parser.add_subparsers(
        dest="orchestrator_command", help="Orchestrator command"
    )

    # orchestrator enable
    orchestrator_enable = orchestrator_subparsers.add_parser(
        "enable", help="Enable orchestrator mode"
    )
    orchestrator_enable.add_argument(
        "--level",
        "-l",
        default="strict",
        choices=["strict", "guidance"],
        help="Enforcement level (default: strict)",
    )
    orchestrator_enable.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # orchestrator disable
    orchestrator_disable = orchestrator_subparsers.add_parser(
        "disable", help="Disable orchestrator mode"
    )
    orchestrator_disable.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # orchestrator status
    orchestrator_status = orchestrator_subparsers.add_parser(
        "status", help="Show orchestrator mode status"
    )
    orchestrator_status.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # orchestrator set-level
    orchestrator_set_level = orchestrator_subparsers.add_parser(
        "set-level", help="Set enforcement level"
    )
    orchestrator_set_level.add_argument(
        "level",
        choices=["strict", "guidance"],
        help="Enforcement level to set",
    )
    orchestrator_set_level.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # orchestrator reset-violations
    orchestrator_reset_violations = orchestrator_subparsers.add_parser(
        "reset-violations", help="Reset violation counter and circuit breaker"
    )
    orchestrator_reset_violations.add_argument(
        "--graph-dir", "-g", default=".htmlgraph", help="Graph directory"
    )

    # install-gemini-extension
    subparsers.add_parser(
        "install-gemini-extension",
        help="Install the Gemini CLI extension from the bundled package",
    )

    # claude - Start Claude Code with orchestrator support
    claude_parser = subparsers.add_parser(
        "claude", help="Start Claude Code with HtmlGraph integration"
    )
    claude_group = claude_parser.add_mutually_exclusive_group()
    claude_group.add_argument(
        "--init",
        action="store_true",
        help="Start with orchestrator system prompt (recommended)",
    )
    claude_group.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Resume last Claude Code session",
    )
    claude_group.add_argument(
        "--dev",
        action="store_true",
        help="Start in development mode with plugin loaded from packages/claude-plugin",
    )
    claude_parser.set_defaults(func=cmd_claude)

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "install-hooks":
        cmd_install_hooks(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "session":
        if args.session_command == "start":
            cmd_session_start(args)
        elif args.session_command == "end":
            cmd_session_end(args)
        elif args.session_command == "list":
            cmd_session_list(args)
        elif args.session_command == "start-info":
            cmd_session_start_info(args)
        elif (
            args.session_command == "status-report" or args.session_command == "resume"
        ):
            cmd_session_status_report(args)
        elif args.session_command == "dedupe":
            cmd_session_dedupe(args)
        elif args.session_command == "link":
            cmd_session_link(args)
        elif args.session_command == "validate-attribution":
            cmd_session_validate_attribution(args)
        elif args.session_command == "handoff":
            cmd_session_handoff(args)
        else:
            session_parser.print_help()
            sys.exit(1)
    elif args.command == "activity":
        # Legacy activity tracking command
        cmd_track(args)
    elif args.command == "transcript":
        # Claude Code transcript integration
        if args.transcript_command == "list":
            cmd_transcript_list(args)
        elif args.transcript_command == "import":
            cmd_transcript_import(args)
        elif args.transcript_command == "link":
            cmd_transcript_link(args)
        elif args.transcript_command == "stats":
            cmd_transcript_stats(args)
        elif args.transcript_command == "auto-link":
            cmd_transcript_auto_link(args)
        elif args.transcript_command == "health":
            cmd_transcript_health(args)
        elif args.transcript_command == "patterns":
            cmd_transcript_patterns(args)
        elif args.transcript_command == "transitions":
            cmd_transcript_transitions(args)
        elif args.transcript_command == "recommendations":
            cmd_transcript_recommendations(args)
        elif args.transcript_command == "insights":
            cmd_transcript_insights(args)
        elif args.transcript_command == "export":
            cmd_transcript_export(args)
        elif args.transcript_command == "track-stats":
            cmd_transcript_track_stats(args)
        elif args.transcript_command == "link-feature":
            cmd_transcript_link_feature(args)
        else:
            transcript_parser.print_help()
            sys.exit(1)
    elif args.command == "track":
        # New track management commands
        if args.track_command == "new":
            cmd_track_new(args)
        elif args.track_command == "list":
            cmd_track_list(args)
        elif args.track_command == "spec":
            cmd_track_spec(args)
        elif args.track_command == "plan":
            cmd_track_plan(args)
        elif args.track_command == "show":
            cmd_track_show(args)
        elif args.track_command == "delete":
            cmd_track_delete(args)
        else:
            track_parser.print_help()
            sys.exit(1)
    elif args.command == "archive":
        # Archive management
        if args.archive_command == "create":
            cmd_archive_create(args)
        elif args.archive_command == "search":
            cmd_archive_search(args)
        elif args.archive_command == "stats":
            cmd_archive_stats(args)
        elif args.archive_command == "restore":
            cmd_archive_restore(args)
        elif args.archive_command == "list":
            cmd_archive_list(args)
        else:
            archive_parser.print_help()
            sys.exit(1)
    elif args.command == "work":
        # Work management with smart routing
        if args.work_command == "next":
            cmd_work_next(args)
        elif args.work_command == "queue":
            cmd_work_queue(args)
        else:
            work_parser.print_help()
            sys.exit(1)
    elif args.command == "agent":
        # Agent management
        if args.agent_command == "list":
            cmd_agent_list(args)
        else:
            agent_parser.print_help()
            sys.exit(1)
    elif args.command == "feature":
        if args.feature_command == "create":
            cmd_feature_create(args)
        elif args.feature_command == "start":
            cmd_feature_start(args)
        elif args.feature_command == "complete":
            cmd_feature_complete(args)
        elif args.feature_command == "primary":
            cmd_feature_primary(args)
        elif args.feature_command == "claim":
            cmd_feature_claim(args)
        elif args.feature_command == "release":
            cmd_feature_release(args)
        elif args.feature_command == "auto-release":
            cmd_feature_auto_release(args)
        elif args.feature_command == "list":
            cmd_feature_list(args)
        elif args.feature_command == "step-complete":
            cmd_feature_step_complete(args)
        elif args.feature_command == "delete":
            cmd_feature_delete(args)
        else:
            feature_parser.print_help()
            sys.exit(1)
    elif args.command == "analytics":
        from htmlgraph.analytics.cli import cmd_analytics

        cmd_analytics(args)
    elif args.command == "docs":
        if args.docs_command == "version":
            cmd_docs_version(args)
        elif args.docs_command == "upgrade":
            cmd_docs_upgrade(args)
        elif args.docs_command == "diff":
            cmd_docs_diff(args)
        elif args.docs_command == "rollback":
            cmd_docs_rollback(args)
        elif args.docs_command == "generate":
            cmd_docs_generate(args)
        else:
            docs_parser.print_help()
            sys.exit(1)
    elif args.command == "events":
        if args.events_command == "export-sessions":
            cmd_events_export(args)
        else:
            events_parser.print_help()
            sys.exit(1)
    elif args.command == "index":
        if args.index_command == "rebuild":
            cmd_index_rebuild(args)
        else:
            index_parser.print_help()
            sys.exit(1)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "git-event":
        cmd_git_event(args)
    elif args.command == "mcp":
        if args.mcp_command == "serve":
            cmd_mcp_serve(args)
        else:
            mcp_parser.print_help()
            sys.exit(1)
    elif args.command == "setup":
        from htmlgraph.setup import (
            setup_all as setup_all_fn,
        )
        from htmlgraph.setup import (
            setup_claude as setup_claude_fn,
        )
        from htmlgraph.setup import (
            setup_codex as setup_codex_fn,
        )
        from htmlgraph.setup import (
            setup_gemini as setup_gemini_fn,
        )

        if args.setup_command == "claude":
            setup_claude_fn(args)
        elif args.setup_command == "codex":
            setup_codex_fn(args)
        elif args.setup_command == "gemini":
            setup_gemini_fn(args)
        elif args.setup_command == "all":
            setup_all_fn(args)
        else:
            setup_parser.print_help()
            sys.exit(1)
    elif args.command == "publish":
        cmd_publish(args)
    elif args.command == "sync-docs":
        cmd_sync_docs(args)
    elif args.command == "deploy":
        if args.deploy_command == "init":
            cmd_deploy_init(args)
        elif args.deploy_command == "run":
            cmd_deploy_run(args)
        else:
            deploy_parser.print_help()
            sys.exit(1)
    elif args.command == "orchestrator":
        if args.orchestrator_command == "enable":
            cmd_orchestrator_enable(args)
        elif args.orchestrator_command == "disable":
            cmd_orchestrator_disable(args)
        elif args.orchestrator_command == "status":
            cmd_orchestrator_status(args)
        elif args.orchestrator_command == "set-level":
            cmd_orchestrator_set_level(args)
        elif args.orchestrator_command == "reset-violations":
            cmd_orchestrator_reset_violations(args)
        else:
            orchestrator_parser.print_help()
            sys.exit(1)
    elif args.command == "install-gemini-extension":
        cmd_install_gemini_extension(args)
    elif args.command == "claude":
        cmd_claude(args)
    else:
        parser.print_help()
        sys.exit(1)


# =============================================================================
# Deployment Commands
# =============================================================================


def cmd_deploy_init(args: argparse.Namespace) -> None:
    """Initialize deployment configuration."""
    from htmlgraph.deploy import create_deployment_config_template

    output_path = Path(args.output or "htmlgraph-deploy.toml")

    if output_path.exists() and not args.force:
        print(
            f"Error: {output_path} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    create_deployment_config_template(output_path)


def cmd_deploy_run(args: argparse.Namespace) -> None:
    """Run deployment process."""
    from htmlgraph.deploy import Deployer, DeploymentConfig

    # Load configuration
    config_path = Path(args.config or "htmlgraph-deploy.toml")

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        print(
            "Run 'htmlgraph deploy init' to create a template configuration.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        config = DeploymentConfig.from_toml(config_path)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle shortcut flags
    skip_steps = []
    only_steps = None

    if args.docs_only:
        only_steps = ["git-push"]
    elif args.build_only:
        only_steps = ["build"]
    elif args.skip_pypi:
        skip_steps.append("pypi-publish")
    elif args.skip_plugins:
        skip_steps.append("update-plugins")

    # Create deployer
    deployer = Deployer(
        config=config,
        dry_run=args.dry_run,
        skip_steps=skip_steps,
        only_steps=only_steps,
    )

    # Run deployment
    deployer.deploy()


# =============================================================================
# Documentation Sync Command
# =============================================================================


def cmd_sync_docs(args: argparse.Namespace) -> int:
    """Synchronize AI agent memory files across platforms."""
    from htmlgraph.sync_docs import (
        check_all_files,
        generate_platform_file,
        sync_all_files,
    )

    project_root = Path(args.project_root or os.getcwd()).resolve()

    if args.check:
        # Check mode
        print("🔍 Checking memory files...")
        results = check_all_files(project_root)

        print("\nStatus:")
        all_good = True
        for filename, status in results.items():
            if filename == "AGENTS.md":
                if status:
                    print(f"  ✅ {filename} exists")
                else:
                    print(f"  ❌ {filename} MISSING (required)")
                    all_good = False
            else:
                if status:
                    print(f"  ✅ {filename} references AGENTS.md")
                else:
                    print(f"  ⚠️  {filename} missing reference")
                    all_good = False

        if all_good:
            print("\n✅ All files are properly synchronized!")
            return 0
        else:
            print("\n⚠️  Some files need attention")
            return 1

    elif args.generate:
        # Generate mode
        platform = args.generate.lower()
        print(f"📝 Generating {platform.upper()} memory file...")

        try:
            content = generate_platform_file(platform, project_root)
            from htmlgraph.sync_docs import PLATFORM_TEMPLATES

            template = PLATFORM_TEMPLATES[platform]
            filepath = project_root / template["filename"]

            if filepath.exists() and not args.force:
                print(f"⚠️  {filepath.name} already exists. Use --force to overwrite.")
                return 1

            filepath.write_text(content)
            print(f"✅ Created: {filepath}")
            print("\nThe file references AGENTS.md for core documentation.")
            return 0

        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1

    else:
        # Sync mode (default)
        print("🔄 Synchronizing memory files...")
        changes = sync_all_files(project_root)

        print("\nResults:")
        for change in changes:
            print(f"  {change}")

        return 1 if any("⚠️" in c or "❌" in c for c in changes) else 0


# =============================================================================
# Archive Management Commands
# =============================================================================


def cmd_archive_create(args: argparse.Namespace) -> None:
    """Create archive from old entities."""
    from pathlib import Path

    from htmlgraph.archive import ArchiveManager

    htmlgraph_dir = Path(args.graph_dir).resolve()

    if not htmlgraph_dir.exists():
        print(f"Error: Directory not found: {htmlgraph_dir}", file=sys.stderr)
        sys.exit(1)

    manager = ArchiveManager(htmlgraph_dir)

    # Run archive operation
    result = manager.archive_entities(
        older_than_days=args.older_than,
        period=args.period,
        dry_run=args.dry_run,
    )

    if result["dry_run"]:
        print("\n🔍 DRY RUN - Preview (no changes made)\n")
        print(f"Would archive: {result['would_archive']} entities")
        print(f"Archive files: {len(result['archive_files'])}")
        print("\nDetails:")
        for archive_key, count in result["details"].items():
            print(f"  {archive_key}: {count} entities")
    else:
        print(f"\n✅ Archived {result['archived_count']} entities")
        print(f"Created {len(result['archive_files'])} archive file(s):")
        for archive_file in result["archive_files"]:
            count = result["details"].get(archive_file.replace(".html", ""), 0)
            print(f"  - {archive_file} ({count} entities)")

    manager.close()


def cmd_archive_search(args: argparse.Namespace) -> None:
    """Search archived entities."""
    import json
    from pathlib import Path

    from htmlgraph.archive import ArchiveManager

    htmlgraph_dir = Path(args.graph_dir).resolve()

    if not htmlgraph_dir.exists():
        print(f"Error: Directory not found: {htmlgraph_dir}", file=sys.stderr)
        sys.exit(1)

    manager = ArchiveManager(htmlgraph_dir)

    # Search archives
    results = manager.search(args.query, limit=args.limit)

    if args.format == "json":
        print(json.dumps({"query": args.query, "results": results}, indent=2))
    else:
        print(f"\n🔍 Search results for: '{args.query}'\n")
        print(f"Found {len(results)} result(s):\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['entity_id']} ({result['entity_type']})")
            print(f"   Archive: {result['archive_file']}")
            print(f"   Status: {result['status']}")
            print(f"   Title: {result['title_snippet']}")
            if result["description_snippet"]:
                print(f"   Description: {result['description_snippet']}")
            print(f"   Relevance: {result['rank']:.2f}")
            print()

    manager.close()


def cmd_archive_stats(args: argparse.Namespace) -> None:
    """Show archive statistics."""
    import json
    from pathlib import Path

    from htmlgraph.archive import ArchiveManager

    htmlgraph_dir = Path(args.graph_dir).resolve()

    if not htmlgraph_dir.exists():
        print(f"Error: Directory not found: {htmlgraph_dir}", file=sys.stderr)
        sys.exit(1)

    manager = ArchiveManager(htmlgraph_dir)

    # Get statistics
    stats = manager.get_archive_stats()

    if args.format == "json":
        print(json.dumps(stats, indent=2))
    else:
        print("\n📊 Archive Statistics\n")
        print(f"Archive files: {stats['archive_count']}")
        print(f"Archived entities: {stats['entity_count']}")
        print(f"Total size: {stats['total_size_mb']:.2f} MB")
        print(f"FTS5 index: {stats['fts_size_mb']:.2f} MB")
        print(
            f"Bloom filters: {stats['bloom_size_kb']:.2f} KB ({stats['bloom_count']} files)"
        )

    manager.close()


def cmd_archive_restore(args: argparse.Namespace) -> None:
    """Restore archived entity."""
    from pathlib import Path

    from htmlgraph.archive import ArchiveManager

    htmlgraph_dir = Path(args.graph_dir).resolve()

    if not htmlgraph_dir.exists():
        print(f"Error: Directory not found: {htmlgraph_dir}", file=sys.stderr)
        sys.exit(1)

    manager = ArchiveManager(htmlgraph_dir)

    # Restore entity
    success = manager.unarchive(args.entity_id)

    if success:
        print(f"✅ Restored {args.entity_id} from archive")
    else:
        print(f"❌ Entity not found in archives: {args.entity_id}", file=sys.stderr)
        sys.exit(1)

    manager.close()


def cmd_archive_list(args: argparse.Namespace) -> None:
    """List all archive files."""
    import json
    from pathlib import Path

    htmlgraph_dir = Path(args.graph_dir).resolve()

    if not htmlgraph_dir.exists():
        print(f"Error: Directory not found: {htmlgraph_dir}", file=sys.stderr)
        sys.exit(1)

    archive_dir = htmlgraph_dir / "archives"

    if not archive_dir.exists():
        print("No archives found")
        return

    archive_files = sorted(archive_dir.glob("*.html"))

    if args.format == "json":
        file_list = [
            {
                "filename": f.name,
                "size_kb": f.stat().st_size / 1024,
                "modified": f.stat().st_mtime,
            }
            for f in archive_files
        ]
        print(json.dumps({"archives": file_list}, indent=2))
    else:
        print(f"\n📦 Archive Files ({len(archive_files)})\n")
        for f in archive_files:
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
