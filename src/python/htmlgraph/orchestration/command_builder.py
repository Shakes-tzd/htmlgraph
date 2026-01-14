from __future__ import annotations

"""Command builder for Claude Code CLI invocations.

Provides fluent interface for constructing Claude CLI commands.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ClaudeCommandBuilder:
    """Fluent builder for Claude Code CLI commands.

    Example:
        >>> builder = ClaudeCommandBuilder()
        >>> cmd = builder.with_resume() \\
        ...     .with_plugin_dir("/path/to/plugin") \\
        ...     .with_system_prompt("System prompt text") \\
        ...     .build()
        >>> # Result: ["claude", "--resume", "--plugin-dir", "/path/to/plugin",
        ...  #          "--append-system-prompt", "System prompt text"]
    """

    def __init__(self) -> None:
        """Initialize with base command."""
        self._cmd: list[str] = ["claude"]

    def with_resume(self) -> ClaudeCommandBuilder:
        """Add --resume flag to resume last session.

        Returns:
            Self for method chaining
        """
        self._cmd.append("--resume")
        return self

    def with_plugin_dir(self, plugin_dir: str | Path) -> ClaudeCommandBuilder:
        """Add --plugin-dir flag.

        Args:
            plugin_dir: Path to plugin directory

        Returns:
            Self for method chaining
        """
        self._cmd.extend(["--plugin-dir", str(plugin_dir)])
        return self

    def with_system_prompt(self, prompt: str) -> ClaudeCommandBuilder:
        """Add --append-system-prompt flag.

        Args:
            prompt: System prompt text to append

        Returns:
            Self for method chaining
        """
        if prompt:  # Only add if prompt is not empty
            self._cmd.extend(["--append-system-prompt", prompt])
        return self

    def build(self) -> list[str]:
        """Build the final command list.

        Returns:
            List of command arguments ready for subprocess.run()
        """
        return self._cmd
