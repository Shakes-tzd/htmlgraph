"""
Deploy entry point for HtmlGraph.

This module provides a Python wrapper around the deploy-all.sh shell script,
enabling programmatic deployment and CI/CD integration via entry points.

Usage:
    htmlgraph-deploy 0.8.0                      # Full deployment
    htmlgraph-deploy --docs-only                # Just commit + push
    htmlgraph-deploy --build-only               # Just build package
    htmlgraph-deploy 0.8.0 --skip-pypi          # Build but don't publish
    htmlgraph-deploy --dry-run                  # Preview actions

For full documentation, see: scripts/README.md
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    # Find pyproject.toml by walking up from this file
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (pyproject.toml not found)")


def run_deploy_script(args: list[str]) -> int:
    """Run the deploy-all.sh script with given arguments."""
    project_root = get_project_root()
    script_path = project_root / "scripts" / "deploy-all.sh"

    if not script_path.exists():
        print(f"Error: Deploy script not found at {script_path}")
        print("This should be installed with the htmlgraph package.")
        return 1

    try:
        result = subprocess.run([str(script_path)] + args, check=False)
        return result.returncode
    except FileNotFoundError:
        print(f"Error: Could not execute {script_path}")
        return 1


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for htmlgraph-deploy command.

    Args:
        argv: Command-line arguments (if None, uses sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        prog="htmlgraph-deploy",
        description="Deploy HtmlGraph package with flexible options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  htmlgraph-deploy 0.8.0                    Full deployment
  htmlgraph-deploy --docs-only              Just commit + push
  htmlgraph-deploy --build-only             Just build package
  htmlgraph-deploy 0.8.0 --skip-pypi        Build but don't publish
  htmlgraph-deploy --dry-run                Preview actions
  htmlgraph-deploy --help                   Show this help

For more information, see: https://github.com/Shakes-tzd/htmlgraph#deployment
        """,
    )

    parser.add_argument(
        "version",
        nargs="?",
        default="",
        help="Version to deploy (auto-detected from pyproject.toml if not specified)",
    )

    parser.add_argument(
        "--docs-only",
        action="store_true",
        help="Only commit and push to git (skip build/publish)",
    )

    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Only build package (skip git/publish/install)",
    )

    parser.add_argument(
        "--skip-pypi",
        action="store_true",
        help="Skip PyPI publishing step",
    )

    parser.add_argument(
        "--skip-plugins",
        action="store_true",
        help="Skip plugin update steps (Claude, Gemini, Codex)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )

    args = parser.parse_args(argv)

    # Build arguments for deploy-all.sh
    deploy_args = []

    # Add version if provided
    if args.version:
        deploy_args.append(args.version)

    # Add flags
    if args.docs_only:
        deploy_args.append("--docs-only")
    if args.build_only:
        deploy_args.append("--build-only")
    if args.skip_pypi:
        deploy_args.append("--skip-pypi")
    if args.skip_plugins:
        deploy_args.append("--skip-plugins")
    if args.dry_run:
        deploy_args.append("--dry-run")

    # Run the shell script
    return run_deploy_script(deploy_args)


if __name__ == "__main__":
    sys.exit(main())
