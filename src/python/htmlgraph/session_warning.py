from __future__ import annotations

"""
Session Warning System for AI Agents.

Provides a mechanism to show critical instructions to AI agents at session start,
working around Claude Code's SessionStart hook bug (#10373) where additionalContext
is not injected for new conversations.

The warning:
1. Shows on every new session (first SDK usage)
2. Contains orchestrator instructions
3. Requires explicit dismissal (confirming agent read it)

Usage:
    from htmlgraph import SDK

    sdk = SDK(agent="claude")
    # Warning automatically shown if not dismissed

    # Agent dismisses after reading (as first action)
    sdk.dismiss_session_warning()
"""


import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# The orchestrator instructions that agents MUST see
ORCHESTRATOR_WARNING = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                     HTMLGRAPH ORCHESTRATOR MODE                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  YOU ARE THE ORCHESTRATOR. Follow these directives:                          ║
║                                                                              ║
║  1. DELEGATE exploration → Task(subagent_type="Explore")                     ║
║  2. DELEGATE implementation → sdk.spawn_coder(feature_id, context)           ║
║  3. CREATE work items BEFORE code changes → sdk.features.create().save()     ║
║  4. PARALLELIZE independent tasks → Multiple Task() calls in ONE message     ║
║  5. USE SDK METHODS not raw prompts → sdk.orchestrate(), sdk.spawn_coder()   ║
║                                                                              ║
║  SDK QUICK REFERENCE:                                                        ║
║    sdk.spawn_coder(feature_id, context)  # Generate coder prompt             ║
║    sdk.spawn_explorer(task, scope)       # Generate explorer prompt          ║
║    sdk.orchestrate(feature_id, scope)    # Full orchestration workflow       ║
║    sdk.plan_parallel_work(max_agents)    # Get parallelizable work           ║
║                                                                              ║
║  ANTI-PATTERNS TO AVOID:                                                     ║
║    ❌ Raw Task prompts without sdk.spawn_coder()                             ║
║    ❌ Sequential Task calls (use ONE message for parallelism)                ║
║    ❌ Code changes without creating a feature first                          ║
║    ❌ Manual file edits on .htmlgraph/ (use SDK instead)                     ║
║                                                                              ║
║  FIRST ACTION: Dismiss this warning to confirm you've read it:               ║
║    >>> sdk.dismiss_session_warning()                                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


class SessionWarning:
    """
    Manages session warning state for AI agents.

    Shows critical orchestrator instructions on first SDK usage,
    requires explicit dismissal to confirm agent read them.
    """

    WARNING_FILE = ".session-warning-state.json"

    def __init__(self, graph_dir: Path):
        self.graph_dir = Path(graph_dir)
        self.state_file = self.graph_dir / self.WARNING_FILE
        self._state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load warning state from file."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "dismissed_at": None,
            "dismissed_by": None,
            "session_id": None,
            "show_count": 0,
        }

    def _save_state(self) -> None:
        """Save warning state to file."""
        try:
            self.state_file.write_text(json.dumps(self._state, indent=2))
        except OSError:
            pass

    def should_show(self, session_id: str | None = None) -> bool:
        """
        Check if warning should be shown.

        Shows warning if:
        - Never dismissed, OR
        - Different session than last dismissal
        """
        # Always show if never dismissed
        if not self._state.get("dismissed_at"):
            return True

        # Show if different session
        if session_id and self._state.get("session_id") != session_id:
            return True

        return False

    def show(self, agent: str | None = None, session_id: str | None = None) -> None:
        """
        Show the warning to stderr (visible to agent).

        Args:
            agent: Agent identifier
            session_id: Current session ID
        """
        self._state["show_count"] = self._state.get("show_count", 0) + 1
        self._save_state()

        # Print to stderr so it's visible to the agent
        print(ORCHESTRATOR_WARNING, file=sys.stderr)

        # Also print dismissal reminder
        print(
            f"\n⚠️  WARNING: Orchestrator instructions shown ({self._state['show_count']} times). "
            f"Dismiss with: sdk.dismiss_session_warning()\n",
            file=sys.stderr,
        )

    def dismiss(self, agent: str | None = None, session_id: str | None = None) -> bool:
        """
        Dismiss the warning for this session.

        Args:
            agent: Agent that dismissed
            session_id: Current session ID

        Returns:
            True if dismissed, False if already dismissed for this session
        """
        was_new = self.should_show(session_id)

        self._state["dismissed_at"] = datetime.now().isoformat()
        self._state["dismissed_by"] = agent
        self._state["session_id"] = session_id
        self._save_state()

        if was_new:
            print(
                "✅ Orchestrator warning dismissed. You may now proceed with delegating work.",
                file=sys.stderr,
            )

        return was_new

    def get_status(self) -> dict[str, Any]:
        """Get current warning status."""
        return {
            "dismissed": bool(self._state.get("dismissed_at")),
            "dismissed_at": self._state.get("dismissed_at"),
            "dismissed_by": self._state.get("dismissed_by"),
            "show_count": self._state.get("show_count", 0),
        }


def check_and_show_warning(
    graph_dir: Path,
    agent: str | None = None,
    session_id: str | None = None,
) -> SessionWarning:
    """
    Check if warning should be shown and show it if needed.

    Called automatically from SDK.__init__.

    Args:
        graph_dir: Path to .htmlgraph directory
        agent: Agent identifier
        session_id: Current session ID

    Returns:
        SessionWarning instance for dismissal
    """
    warning = SessionWarning(graph_dir)

    if warning.should_show(session_id):
        warning.show(agent=agent, session_id=session_id)

    return warning
