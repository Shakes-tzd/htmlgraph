"""Subprocess execution with standardized error handling.

Provides consistent error handling for Claude Code CLI invocations.
"""

from __future__ import annotations

import subprocess
import sys


class SubprocessRunner:
    """Execute subprocess commands with error handling."""

    @staticmethod
    def run_claude_command(cmd: list[str]) -> None:
        """Execute Claude Code CLI command with error handling.

        Args:
            cmd: Command list (e.g., ["claude", "--resume"])

        Raises:
            SystemExit: If 'claude' command not found or other error
        """
        try:
            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            print("Error: 'claude' command not found.", file=sys.stderr)
            print(
                "Please install Claude Code CLI: https://code.claude.com",
                file=sys.stderr,
            )
            sys.exit(1)
