"""Plugin management for HtmlGraph Claude Code integration.

Centralizes plugin installation, directory management, and validation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PluginManager:
    """Manage HtmlGraph Claude plugin installation and directories."""

    @staticmethod
    def get_plugin_dir() -> Path:
        """Get the plugin directory path.

        Returns:
            Path to packages/claude-plugin (the plugin root, not .claude-plugin)
        """
        # Path(__file__) = .../src/python/htmlgraph/orchestration/plugin_manager.py
        # Need to go up 5 levels to reach project root
        return (
            Path(__file__).parent.parent.parent.parent.parent
            / "packages"
            / "claude-plugin"
        )

    @staticmethod
    def install_or_update(verbose: bool = True) -> None:
        """Install or update HtmlGraph plugin.

        Args:
            verbose: Whether to show progress messages
        """
        if verbose:
            print("\n📦 Installing/upgrading HtmlGraph plugin...\n")

        # Step 1: Update marketplace
        try:
            if verbose:
                print("  Updating marketplace...")
            result = subprocess.run(
                ["claude", "plugin", "marketplace", "update", "htmlgraph"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                if verbose:
                    print("    ✓ Marketplace updated")
            else:
                # Non-blocking errors
                if (
                    "not found" in result.stderr.lower()
                    or "no marketplace" in result.stderr.lower()
                ):
                    if verbose:
                        print("    ℹ Marketplace not configured (OK, continuing)")
                elif verbose:
                    print(f"    ⚠ Marketplace update: {result.stderr.strip()}")
        except FileNotFoundError:
            if verbose:
                print("    ⚠ 'claude' command not found")
        except Exception as e:
            if verbose:
                print(f"    ⚠ Error updating marketplace: {e}")

        # Step 2: Try update, fallback to install
        try:
            if verbose:
                print("  Updating plugin to latest version...")
            result = subprocess.run(
                ["claude", "plugin", "update", "htmlgraph"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                if verbose:
                    print("    ✓ Plugin updated successfully")
            else:
                # Fallback to install
                if (
                    "not installed" in result.stderr.lower()
                    or "not found" in result.stderr.lower()
                ):
                    if verbose:
                        print("    ℹ Plugin not yet installed, installing...")
                    install_result = subprocess.run(
                        ["claude", "plugin", "install", "htmlgraph"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if install_result.returncode == 0:
                        if verbose:
                            print("    ✓ Plugin installed successfully")
                    elif verbose:
                        print(f"    ⚠ Plugin install: {install_result.stderr.strip()}")
                elif verbose:
                    print(f"    ⚠ Plugin update: {result.stderr.strip()}")
        except FileNotFoundError:
            if verbose:
                print("    ⚠ 'claude' command not found")
        except Exception as e:
            if verbose:
                print(f"    ⚠ Error updating plugin: {e}")

        if verbose:
            print("\n✓ Plugin installation complete\n")

    @staticmethod
    def validate_plugin_dir(plugin_dir: Path) -> None:
        """Validate that plugin directory exists, exit if not.

        Args:
            plugin_dir: Path to plugin directory

        Raises:
            SystemExit: If plugin directory doesn't exist
        """
        if not plugin_dir.exists():
            print(f"Error: Plugin directory not found: {plugin_dir}", file=sys.stderr)
            print(
                "Expected location: packages/claude-plugin/.claude-plugin",
                file=sys.stderr,
            )
            sys.exit(1)
