"""Orchestrator mode validation for PreToolUse hook."""

import re
from pathlib import Path
from typing import Any, Literal

ValidationResult = tuple[Literal["allow", "warn", "block"], str]


class OrchestratorValidator:
    """Validates tool usage against orchestrator delegation rules."""

    def __init__(self, htmlgraph_dir: Path = Path(".htmlgraph")):
        self.htmlgraph_dir = htmlgraph_dir

    def validate_tool_use(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        active_work_items: list[str] | None = None,
    ) -> ValidationResult:
        """
        Validate if tool usage follows orchestrator rules.

        Returns:
            ("allow", reason) - Tool use is permitted
            ("warn", reason) - Tool use allowed but warned
            ("block", reason) - Tool use is blocked
        """
        # SDK operations always allowed
        if self._is_sdk_operation(tool_name, tool_args):
            return ("allow", "SDK operations always permitted")

        # Strategic tools always allowed
        if tool_name in ["Task", "AskUserQuestion", "TodoWrite"]:
            return ("allow", "Strategic tool permitted")

        # Read operations always allowed (exploration)
        if tool_name == "Read":
            return ("allow", "Read operations permitted for exploration")

        # Check if this is a tactical operation that should be delegated
        if tool_name == "Bash":
            return self._validate_bash(tool_args, active_work_items)

        if tool_name in ["Edit", "Write"]:
            return self._validate_code_change(tool_name, tool_args, active_work_items)

        # Default: allow other tools
        return ("allow", "Tool not subject to orchestrator rules")

    def _is_sdk_operation(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Check if this is an SDK operation (creating features, spikes, etc.)."""
        if tool_name == "Bash":
            command = args.get("command", "")
            # Check for SDK operations
            if "from htmlgraph import SDK" in command:
                return True
            if "sdk.features" in command or "sdk.spikes" in command:
                return True
            if "sdk.bugs" in command or "sdk.chores" in command:
                return True
        return False

    def _validate_bash(
        self, args: dict[str, Any], active_work_items: list[str] | None
    ) -> ValidationResult:
        """Validate Bash tool usage."""
        command = args.get("command", "")

        # Check for git operations
        if self._is_git_operation(command):
            return (
                "block",
                f"Git operations must be delegated to subagent. "
                f"Command: {command[:100]}",
            )

        # Check for test operations on multiple files
        if self._is_test_operation(command):
            return (
                "warn",
                f"Consider delegating test execution to test-runner agent. "
                f"Command: {command[:100]}",
            )

        # Allow other bash operations
        return ("allow", "Bash operation permitted")

    def _validate_code_change(
        self,
        tool_name: str,
        args: dict[str, Any],
        active_work_items: list[str] | None,
    ) -> ValidationResult:
        """Validate Edit/Write tool usage."""
        file_path = args.get("file_path", "")

        # Check if modifying .htmlgraph files (should use SDK)
        if ".htmlgraph/" in file_path:
            return (
                "block",
                f"Use SDK to modify .htmlgraph files, not {tool_name} tool. "
                f"File: {file_path}",
            )

        # For now, allow code changes (multi-file detection is in pre-work validator)
        return ("allow", f"{tool_name} operation permitted")

    def _is_git_operation(self, command: str) -> bool:
        """Check if command is a git operation."""
        git_patterns = [
            r"\bgit\s+add\b",
            r"\bgit\s+commit\b",
            r"\bgit\s+push\b",
            r"\bgit\s+pull\b",
            r"\bgit\s+merge\b",
            r"\bgit\s+branch\b",
            r"\bgit\s+checkout\b",
            r"\bgit\s+rebase\b",
        ]
        return any(re.search(pattern, command) for pattern in git_patterns)

    def _is_test_operation(self, command: str) -> bool:
        """Check if command runs tests."""
        test_patterns = [
            r"\bpytest\b",
            r"\bpython\s+-m\s+pytest\b",
            r"\buv\s+run\s+pytest\b",
            r"\bnpm\s+test\b",
            r"\byarn\s+test\b",
        ]
        return any(re.search(pattern, command) for pattern in test_patterns)
