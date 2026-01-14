import logging

logger = logging.getLogger(__name__)

"""
CIGS PreToolUse Enforcer - Enhanced Orchestrator Enforcement with Escalation

Integrates the Computational Imperative Guidance System (CIGS) into the PreToolUse
hook for intelligent delegation enforcement with escalating guidance.

Architecture:
1. Uses existing OrchestratorValidator for base classification
2. Loads session violation count from ViolationTracker
3. Classifies operation using CostCalculator
4. Generates imperative message with escalation via ImperativeMessageGenerator
5. Records violation if should_delegate=True
6. Returns hookSpecificOutput with imperative message

Escalation Levels:
- Level 0 (0 violations): Guidance - informative, no cost shown
- Level 1 (1 violation): Imperative - commanding, includes cost
- Level 2 (2 violations): Final Warning - urgent, includes consequences
- Level 3 (3+ violations): Circuit Breaker - blocking, requires acknowledgment

Design Reference:
    .htmlgraph/spikes/computational-imperative-guidance-system-design.md
    Part 2: CIGS PreToolUse Hook Integration
    Part 4: Imperative Message Generation
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from htmlgraph.cigs.cost import CostCalculator
from htmlgraph.cigs.messaging import ImperativeMessageGenerator
from htmlgraph.cigs.tracker import ViolationTracker
from htmlgraph.hooks.orchestrator import is_allowed_orchestrator_operation
from htmlgraph.orchestrator_mode import OrchestratorModeManager


class CIGSPreToolEnforcer:
    """
    CIGS-enhanced PreToolUse enforcement with escalating imperative messages.

    Integrates all CIGS components for comprehensive delegation enforcement.
    """

    # Tools that are ALWAYS allowed (orchestrator core)
    ALWAYS_ALLOWED = {"Task", "AskUserQuestion", "TodoWrite"}

    # Exploration tools that require delegation after first use
    EXPLORATION_TOOLS = {"Read", "Grep", "Glob"}

    # Implementation tools that always require delegation
    IMPLEMENTATION_TOOLS = {"Edit", "Write", "NotebookEdit", "Delete"}

    def __init__(self, graph_dir: Path | None = None):
        """
        Initialize CIGS PreToolUse enforcer.

        Args:
            graph_dir: Root directory for HtmlGraph (defaults to .htmlgraph)
        """
        if graph_dir is None:
            graph_dir = self._find_graph_dir()

        self.graph_dir = graph_dir
        self.manager = OrchestratorModeManager(graph_dir)
        self.cost_calculator = CostCalculator()
        self.message_generator = ImperativeMessageGenerator()
        self.tracker = ViolationTracker(graph_dir)

        # Ensure session ID is set (detect from environment or use current session)
        if self.tracker._session_id is None:
            self.tracker.set_session_id(self._get_or_create_session_id())

    def _find_graph_dir(self) -> Path:
        """Find .htmlgraph directory starting from cwd."""
        cwd = Path.cwd()
        graph_dir = cwd / ".htmlgraph"

        if not graph_dir.exists():
            for parent in [cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
                candidate = parent / ".htmlgraph"
                if candidate.exists():
                    graph_dir = candidate
                    break

        return graph_dir

    def enforce(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Enforce CIGS delegation rules with escalating guidance.

        Args:
            tool: Tool name (Read, Edit, Bash, etc.)
            params: Tool parameters

        Returns:
            Hook response dict in Claude Code standard format:
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow" | "deny",
                    "additionalContext": "...",  # If allow with guidance
                    "permissionDecisionReason": "...",  # If deny
                }
            }
        """
        # Check if orchestrator mode is enabled
        if not self.manager.is_enabled():
            return self._allow()

        enforcement_level = self.manager.get_enforcement_level()

        # ALWAYS ALLOWED tools pass through
        if tool in self.ALWAYS_ALLOWED:
            return self._allow()

        # Check if SDK operation (always allowed)
        if self._is_sdk_operation(tool, params):
            return self._allow()

        # Get session violation summary
        summary = self.tracker.get_session_violations()
        violation_count = summary.total_violations

        # Check circuit breaker (3+ violations)
        if violation_count >= 3 and enforcement_level == "strict":
            return self._circuit_breaker(violation_count)

        # Classify operation using existing orchestrator logic
        is_allowed, reason, category = is_allowed_orchestrator_operation(tool, params)

        # CIGS enforces stricter rules in strict mode:
        # - Even "single lookups" should be delegated (exploration tools)
        # - All implementation tools should be delegated
        should_delegate = False
        if enforcement_level == "strict":
            if tool in self.EXPLORATION_TOOLS or tool in self.IMPLEMENTATION_TOOLS:
                should_delegate = True
                # Override is_allowed - CIGS wants delegation even for first use
                is_allowed = False

        # If orchestrator allows and CIGS doesn't override, proceed
        if is_allowed and not should_delegate:
            return self._allow()

        # Operation should be delegated - classify with cost analysis
        classification = self.cost_calculator.classify_operation(
            tool=tool,
            params=params,
            is_exploration_sequence=self._is_exploration_sequence(tool),
        )

        # Generate imperative message with escalation
        imperative_message = self.message_generator.generate(
            tool=tool,
            classification=classification,
            violation_count=violation_count,
            autonomy_level=enforcement_level,
        )

        # Record violation for session tracking
        predicted_waste = classification.predicted_cost - classification.optimal_cost
        self.tracker.record_violation(
            tool=tool,
            params=params,
            classification=classification,
            predicted_waste=predicted_waste,
        )

        # Return response based on enforcement level and escalation
        if enforcement_level == "strict":
            # STRICT mode - deny with imperative message
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": imperative_message,
                }
            }
        else:
            # GUIDANCE mode - allow but with strong message
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "additionalContext": imperative_message,
                }
            }

    def _allow(self) -> dict[str, Any]:
        """Return allow response."""
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }

    def _circuit_breaker(self, violation_count: int) -> dict[str, Any]:
        """Return circuit breaker blocking response."""
        message = (
            "🚨 CIRCUIT BREAKER TRIGGERED\n\n"
            f"You have violated delegation rules {violation_count} times this session.\n\n"
            "**Violations detected:**\n"
            "- Direct execution instead of delegation\n"
            "- Context waste on tactical operations\n"
            "- Ignored imperative guidance messages\n\n"
            "**REQUIRED:** Acknowledge violations before proceeding:\n"
            "`uv run htmlgraph orchestrator acknowledge-violation`\n\n"
            "**OR** Change enforcement settings:\n"
            "- Disable: `uv run htmlgraph orchestrator disable`\n"
            "- Guidance mode: `uv run htmlgraph orchestrator set-level guidance`\n"
            "- Reset violations: `uv run htmlgraph orchestrator reset-violations`"
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": message,
            }
        }

    def _is_sdk_operation(self, tool: str, params: dict[str, Any]) -> bool:
        """Check if operation is an SDK operation (always allowed)."""
        if tool != "Bash":
            return False

        command = params.get("command", "")

        # Allow htmlgraph SDK commands
        if command.startswith("uv run htmlgraph ") or command.startswith("htmlgraph "):
            return True

        # Allow git read-only commands
        if command.startswith(("git status", "git diff", "git log")):
            return True

        # Allow SDK inline usage
        if "from htmlgraph import" in command or "import htmlgraph" in command:
            return True

        return False

    def _is_exploration_sequence(self, tool: str) -> bool:
        """Check if this is part of an exploration sequence."""
        if tool not in self.EXPLORATION_TOOLS:
            return False

        # Check recent history for exploration pattern
        # This is simplified - could use tool_history from orchestrator.py
        summary = self.tracker.get_session_violations()

        # If we've already had exploration violations, this is a sequence
        exploration_violations = [
            v for v in summary.violations if v.tool in self.EXPLORATION_TOOLS
        ]

        return len(exploration_violations) >= 1

    def _get_or_create_session_id(self) -> str:
        """Get or create a session ID for tracking."""
        # Try to get from environment
        if "HTMLGRAPH_SESSION_ID" in os.environ:
            return os.environ["HTMLGRAPH_SESSION_ID"]

        # Try to get from session manager
        try:
            from htmlgraph.session_manager import SessionManager

            sm = SessionManager(self.graph_dir)
            current = sm.get_active_session()
            if current:
                return str(current.id)
        except Exception:
            pass

        # Fallback: create a session ID for this test/run
        # Use a consistent ID for the process
        if not hasattr(self.__class__, "_fallback_session_id"):
            from uuid import uuid4

            fallback_id: str = f"test-session-{uuid4().hex[:8]}"
            setattr(self.__class__, "_fallback_session_id", fallback_id)
            return fallback_id

        return str(getattr(self.__class__, "_fallback_session_id"))


def enforce_cigs_pretool(tool_input: dict[str, Any]) -> dict[str, Any]:
    """
    Main entry point for CIGS PreToolUse enforcement.

    Args:
        tool_input: Hook input with tool name and parameters

    Returns:
        Hook response dict in Claude Code standard format
    """
    # Extract tool and params from input
    tool = tool_input.get("name", "") or tool_input.get("tool_name", "")
    params = tool_input.get("input", {}) or tool_input.get("tool_input", {})

    # Create enforcer and run
    try:
        enforcer = CIGSPreToolEnforcer()
        return enforcer.enforce(tool, params)
    except Exception as e:
        # Graceful degradation - allow on error
        logger.warning(f"Warning: CIGS enforcement error: {e}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
            }
        }


def main() -> None:
    """Hook entry point for script wrapper."""
    # Check environment overrides
    if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
        sys.exit(0)

    if os.environ.get("HTMLGRAPH_ORCHESTRATOR_DISABLED") == "1":
        print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
        sys.exit(0)

    # Read tool input from stdin
    try:
        tool_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        tool_input = {}

    # Run CIGS enforcement
    result = enforce_cigs_pretool(tool_input)

    # Output response
    print(json.dumps(result))

    # Exit code based on permission decision
    permission = result.get("hookSpecificOutput", {}).get("permissionDecision", "allow")
    sys.exit(0 if permission == "allow" else 1)


if __name__ == "__main__":
    main()
