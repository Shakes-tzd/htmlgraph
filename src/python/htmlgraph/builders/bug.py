from __future__ import annotations

"""
Bug builder for creating bug report nodes.

Extends BaseBuilder with bug-specific methods like
severity and reproduction steps.
"""


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class BugBuilder(BaseBuilder["BugBuilder"]):
    """
    Fluent builder for creating bugs.

    Inherits common builder methods from BaseBuilder and adds
    bug-specific methods for issue tracking:
    - severity: Bug severity level
    - repro_steps: Steps to reproduce
    - expected/actual: Expected vs actual behavior
    - affected_version: Version where bug occurs

    Example:
        >>> sdk = SDK(agent="claude")
        >>> bug = sdk.bugs.create("Login button unresponsive") \\
        ...     .set_priority("critical") \\
        ...     .set_severity("high") \\
        ...     .set_repro_steps(["Go to login", "Click button", "Nothing happens"]) \\
        ...     .save()
    """

    node_type = "bug"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize bug builder with agent attribution."""
        super().__init__(sdk, title, **kwargs)
        # Auto-assign agent from SDK for work tracking
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # Log warning if agent not assigned (defensive check)
            import logging

            logging.warning(
                f"Creating bug '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "Pass agent='name' to SDK() initialization."
            )

    def set_severity(self, severity: str) -> BugBuilder:
        """
        Set bug severity level.

        Args:
            severity: Severity level (low, medium, high, critical)

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_severity("critical")
        """
        self._data["severity"] = severity
        return self

    def set_repro_steps(self, steps: list[str]) -> BugBuilder:
        """
        Set steps to reproduce the bug.

        Args:
            steps: List of reproduction steps

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_repro_steps(["Open app", "Click login", "Enter credentials"])
        """
        self._data["repro_steps"] = steps
        return self

    def set_expected_behavior(self, expected: str) -> BugBuilder:
        """
        Set expected behavior.

        Args:
            expected: What should happen

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_expected_behavior("User should be logged in")
        """
        self._data["expected_behavior"] = expected
        return self

    def set_actual_behavior(self, actual: str) -> BugBuilder:
        """
        Set actual (buggy) behavior.

        Args:
            actual: What actually happens

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_actual_behavior("Button does nothing")
        """
        self._data["actual_behavior"] = actual
        return self

    def set_affected_version(self, version: str) -> BugBuilder:
        """
        Set the affected version.

        Args:
            version: Version string where bug occurs

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_affected_version("1.2.3")
        """
        self._data["affected_version"] = version
        return self

    def set_environment(self, environment: str) -> BugBuilder:
        """
        Set the environment where bug occurs.

        Args:
            environment: Environment description (e.g., "Chrome 120, macOS")

        Returns:
            Self for method chaining

        Example:
            >>> bug.set_environment("Chrome 120, macOS Sonoma")
        """
        self._data["environment"] = environment
        return self
