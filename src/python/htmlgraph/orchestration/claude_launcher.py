from __future__ import annotations

"""Claude Code launcher with multiple integration modes.

Coordinates launching Claude Code with various HtmlGraph integration options.
"""

import argparse
import logging
import sys
from pathlib import Path

from htmlgraph.orchestration.command_builder import ClaudeCommandBuilder
from htmlgraph.orchestration.plugin_manager import PluginManager
from htmlgraph.orchestration.prompts import get_orchestrator_prompt
from htmlgraph.orchestration.subprocess_runner import SubprocessRunner

logger = logging.getLogger(__name__)


class ClaudeLauncher:
    """Launch Claude Code with various HtmlGraph integration modes.

    Supports four launch scenarios:
    1. --init: Orchestrator mode with plugin installation
    2. --continue: Resume last session with orchestrator rules
    3. --dev: Development mode with local plugin
    4. default: Minimal orchestrator rules
    """

    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize launcher with parsed arguments.

        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.interactive = not (args.quiet or args.format == "json")

    def launch(self) -> None:
        """Main entry point - routes to appropriate scenario.

        Raises:
            SystemExit: On error during launch
        """
        try:
            if self.args.init:
                self._launch_orchestrator_mode()
            elif self.args.continue_session:
                self._launch_resume_mode()
            elif self.args.dev:
                self._launch_dev_mode()
            else:
                self._launch_default_mode()
        except Exception as e:
            logger.warning(f"Error: Failed to start Claude Code: {e}")
            sys.exit(1)

    def _launch_orchestrator_mode(self) -> None:
        """Launch with orchestrator prompt (--init).

        Installs plugin, loads orchestrator system prompt, and starts Claude Code
        in orchestrator mode with multi-AI delegation rules.
        """
        # Install plugin
        PluginManager.install_or_update(verbose=self.interactive)

        # Load prompt
        prompt = get_orchestrator_prompt(include_dev_mode=False)

        # Show banner
        if self.interactive:
            self._print_orchestrator_banner()

        # Build command
        cmd = ClaudeCommandBuilder().with_system_prompt(prompt).build()

        # Execute
        SubprocessRunner.run_claude_command(cmd)

    def _launch_resume_mode(self) -> None:
        """Resume last session with orchestrator rules (--continue).

        Installs plugin, loads plugin directory, and resumes the last Claude Code
        session with orchestrator system prompt.
        """
        # Install plugin
        PluginManager.install_or_update(verbose=self.interactive)

        # Get plugin directory
        plugin_dir = PluginManager.get_plugin_dir()

        # Load prompt
        prompt = get_orchestrator_prompt(include_dev_mode=False)

        # Show status
        if self.interactive:
            logger.info("Resuming last Claude Code session...")
            logger.info("  ✓ Multi-AI delegation rules injected")

        # Build command
        builder = ClaudeCommandBuilder().with_resume().with_system_prompt(prompt)

        # Add plugin directory if exists
        if plugin_dir.exists():
            builder.with_plugin_dir(str(plugin_dir))
            if self.interactive:
                logger.info(f"  ✓ Loading plugin from: {plugin_dir}")

        cmd = builder.build()

        # Execute
        SubprocessRunner.run_claude_command(cmd)

    def _launch_dev_mode(self) -> None:
        """Launch with local plugin for development (--dev).

        Loads plugin from local source directory for development/testing.
        Changes to plugin files take effect after restart.
        """
        # Get and validate plugin directory
        plugin_dir = PluginManager.get_plugin_dir()
        PluginManager.validate_plugin_dir(plugin_dir)

        # Load prompt with dev mode
        prompt = get_orchestrator_prompt(include_dev_mode=True)

        # Show banner
        if self.interactive:
            self._print_dev_mode_banner(plugin_dir)

        # Build command
        cmd = (
            ClaudeCommandBuilder()
            .with_plugin_dir(str(plugin_dir))
            .with_system_prompt(prompt)
            .build()
        )

        # Execute
        SubprocessRunner.run_claude_command(cmd)

    def _launch_default_mode(self) -> None:
        """Launch with minimal orchestrator rules (default).

        Starts Claude Code with basic multi-AI delegation rules but no plugin.
        """
        # Load prompt
        prompt = get_orchestrator_prompt(include_dev_mode=False)

        # Show status
        if self.interactive:
            logger.info("Starting Claude Code with multi-AI delegation rules...")

        # Build command
        cmd = ClaudeCommandBuilder().with_system_prompt(prompt).build()

        # Execute
        SubprocessRunner.run_claude_command(cmd)

    def _print_orchestrator_banner(self) -> None:
        """Print orchestrator mode banner."""
        print("=" * 60)
        logger.info("🤖 HtmlGraph Orchestrator Mode")
        print("=" * 60)
        logger.info("\nStarting Claude Code with orchestrator system prompt...")
        logger.info("Key directives:")
        logger.info("  ✓ Delegate to Gemini (FREE), Codex, Copilot first")
        logger.info("  ✓ Use Task() only as fallback")
        logger.info("  ✓ Create work items before delegating")
        logger.info("  ✓ Track all work in .htmlgraph/")
        print()

    def _print_dev_mode_banner(self, plugin_dir: Path) -> None:
        """Print development mode banner.

        Args:
            plugin_dir: Path to local plugin directory
        """
        print("=" * 60)
        logger.info("🔧 HtmlGraph Development Mode")
        print("=" * 60)
        logger.info(f"\nLoading plugin from: {plugin_dir}")
        logger.info("  ✓ Skills, agents, and hooks will be loaded from local files")
        logger.info("  ✓ Orchestrator system prompt will be appended")
        logger.info("  ✓ Multi-AI delegation rules will be injected")
        logger.info("  ✓ Changes to plugin files will take effect after restart")
        print()
