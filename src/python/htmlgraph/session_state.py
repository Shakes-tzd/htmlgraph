"""
SessionStateManager - Automatic session state and environment variable management.

Provides automatic detection and management of:
- Current session state (ID, source, compaction status)
- Environment variable setup (CLAUDE_SESSION_ID, CLAUDE_SESSION_SOURCE, etc.)
- Delegation status determination
- Session metadata recording

Integration with SessionStart hook:
    from htmlgraph import SDK

    sdk = SDK()
    state = sdk.sessions.get_current_state()
    sdk.sessions.setup_environment_variables(state)

    # All environment variables now set automatically
    # Delegation status available via state['delegation_enabled']
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class SessionState(TypedDict, total=False):
    """Current session state information."""

    session_id: str
    session_source: str  # "startup", "resume", "compact", "clear"
    is_post_compact: bool
    previous_session_id: str | None
    delegation_enabled: bool
    prompt_injected: bool
    session_valid: bool
    timestamp: str
    compact_metadata: dict[str, Any]


class SessionStateManager:
    """
    Manages session state detection and environment variable setup.

    Automatically detects:
    - Current session ID and source
    - Post-compact state
    - Delegation status
    - Session validity

    Provides environment variable management:
    - CLAUDE_SESSION_ID
    - CLAUDE_SESSION_SOURCE
    - CLAUDE_SESSION_COMPACTED
    - CLAUDE_DELEGATION_ENABLED
    - CLAUDE_ORCHESTRATOR_ACTIVE
    - CLAUDE_PROMPT_PERSISTENCE_VERSION
    """

    # Session state metadata file
    CURRENT_SESSION_FILE = "current.json"
    SESSION_STATE_FILE = "session_state.json"
    COMPACT_MARKER_FILE = ".compacted"

    def __init__(self, graph_dir: str | Path):
        """
        Initialize SessionStateManager.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.sessions_dir = self.graph_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def get_current_state(self) -> SessionState:
        """
        Get current session state with automatic detection.

        Returns:
            SessionState dict with:
            - session_id: Current session identifier
            - session_source: "startup", "resume", "compact", "clear"
            - is_post_compact: True if this is post-compact
            - previous_session_id: Previous session ID if available
            - delegation_enabled: Should delegation be active
            - prompt_injected: Was orchestrator prompt injected
            - session_valid: Is session valid for work
            - timestamp: Current UTC timestamp
            - compact_metadata: Compact detection details
        """
        # Get current session ID from environment or generate
        session_id = os.environ.get("CLAUDE_SESSION_ID")
        if not session_id:
            session_id = self._generate_session_id()

        # Load previous state
        prev_state = self._load_previous_state()

        # Detect session source and compaction
        source, is_post_compact, compact_metadata = self._detect_session_source(
            session_id, prev_state
        )

        # Determine delegation status
        delegation_enabled = self._should_enable_delegation(is_post_compact, prev_state)

        # Check if session is valid
        session_valid = self._is_session_valid(session_id, prev_state)

        # Get previous session ID
        previous_session_id = prev_state.get("session_id") if prev_state else None

        # Check if orchestrator prompt was injected
        prompt_injected = os.environ.get("CLAUDE_ORCHESTRATOR_ACTIVE") == "true"

        state: SessionState = {
            "session_id": session_id,
            "session_source": source,
            "is_post_compact": is_post_compact,
            "previous_session_id": previous_session_id,
            "delegation_enabled": delegation_enabled,
            "prompt_injected": prompt_injected,
            "session_valid": session_valid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compact_metadata": compact_metadata,
        }

        return state

    def setup_environment_variables(
        self,
        session_state: SessionState | None = None,
        auto_detect_compact: bool = True,
    ) -> dict[str, str]:
        """
        Automatically set up environment variables for session state.

        Args:
            session_state: Session state dict (auto-detected if not provided)
            auto_detect_compact: Whether to auto-detect post-compact state

        Returns:
            Dict of environment variables that were set

        Sets the following environment variables:
        - CLAUDE_SESSION_ID: Current session identifier
        - CLAUDE_SESSION_SOURCE: "startup|resume|compact|clear"
        - CLAUDE_SESSION_COMPACTED: "true|false"
        - CLAUDE_DELEGATION_ENABLED: "true|false"
        - CLAUDE_PREVIOUS_SESSION_ID: Previous session ID
        - CLAUDE_ORCHESTRATOR_ACTIVE: "true|false"
        - CLAUDE_PROMPT_PERSISTENCE_VERSION: "1.0"
        """
        if session_state is None:
            session_state = self.get_current_state()

        env_vars = {}

        # CLAUDE_SESSION_ID - always set
        session_id = session_state.get("session_id", "unknown")
        os.environ["CLAUDE_SESSION_ID"] = session_id
        env_vars["CLAUDE_SESSION_ID"] = session_id

        # CLAUDE_SESSION_SOURCE - session type detection
        source = session_state.get("session_source", "startup")
        os.environ["CLAUDE_SESSION_SOURCE"] = source
        env_vars["CLAUDE_SESSION_SOURCE"] = source

        # CLAUDE_SESSION_COMPACTED - post-compact detection
        is_post_compact = session_state.get("is_post_compact", False)
        os.environ["CLAUDE_SESSION_COMPACTED"] = str(is_post_compact).lower()
        env_vars["CLAUDE_SESSION_COMPACTED"] = str(is_post_compact).lower()

        # CLAUDE_DELEGATION_ENABLED - orchestrator delegation
        delegation_enabled = session_state.get("delegation_enabled", False)
        os.environ["CLAUDE_DELEGATION_ENABLED"] = str(delegation_enabled).lower()
        env_vars["CLAUDE_DELEGATION_ENABLED"] = str(delegation_enabled).lower()

        # CLAUDE_PREVIOUS_SESSION_ID - for tracking continuity
        prev_session = session_state.get("previous_session_id")
        if prev_session:
            os.environ["CLAUDE_PREVIOUS_SESSION_ID"] = prev_session
            env_vars["CLAUDE_PREVIOUS_SESSION_ID"] = prev_session

        # CLAUDE_ORCHESTRATOR_ACTIVE - skill activation
        orchestrator_active = session_state.get("delegation_enabled", False)
        os.environ["CLAUDE_ORCHESTRATOR_ACTIVE"] = str(orchestrator_active).lower()
        env_vars["CLAUDE_ORCHESTRATOR_ACTIVE"] = str(orchestrator_active).lower()

        # CLAUDE_PROMPT_PERSISTENCE_VERSION - version management
        os.environ["CLAUDE_PROMPT_PERSISTENCE_VERSION"] = "1.0"
        env_vars["CLAUDE_PROMPT_PERSISTENCE_VERSION"] = "1.0"

        # Record state metadata
        self.record_state(
            session_id=session_id,
            source=source,
            is_post_compact=is_post_compact,
            delegation_enabled=delegation_enabled,
            environment_vars=env_vars,
        )

        return env_vars

    def record_state(
        self,
        session_id: str,
        source: str,
        is_post_compact: bool,
        delegation_enabled: bool,
        environment_vars: dict[str, str] | None = None,
    ) -> None:
        """
        Store session state metadata for future reference.

        Args:
            session_id: Current session ID
            source: Session source ("startup", "resume", "compact", "clear")
            is_post_compact: Whether this is post-compact
            delegation_enabled: Whether delegation is enabled
            environment_vars: Environment variables that were set
        """
        state_file = self.sessions_dir / self.SESSION_STATE_FILE

        state_data = {
            "session_id": session_id,
            "source": source,
            "is_post_compact": is_post_compact,
            "delegation_enabled": delegation_enabled,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment_vars": environment_vars or {},
        }

        try:
            state_file.write_text(json.dumps(state_data, indent=2))
        except Exception as e:
            logger.warning(f"Could not record session state: {e}")

    def detect_compact_automatically(self) -> bool:
        """
        Auto-detect if this is post-compact by comparing session IDs.

        Returns:
            True if this is a post-compact session
        """
        current_id = os.environ.get("CLAUDE_SESSION_ID")
        prev_state = self._load_previous_state()

        if not current_id or not prev_state:
            return False

        prev_id = prev_state.get("session_id")
        if current_id == prev_id:
            return False  # Same session, not post-compact

        # Check if previous session was ended gracefully (SessionEnd hook called)
        # This is a heuristic: if previous session exists and is marked as "ended",
        # then this new session is likely post-compact
        prev_session_ended = bool(prev_state.get("is_ended", False))
        return prev_session_ended

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _generate_session_id(self) -> str:
        """Generate a stable session ID."""
        from htmlgraph.ids import generate_id

        return generate_id("session", "auto")

    def _load_previous_state(self) -> dict[str, Any] | None:
        """Load previous session state from file."""
        state_file = self.sessions_dir / self.SESSION_STATE_FILE

        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text())
            assert isinstance(data, dict)
            return data
        except Exception as e:
            logger.debug(f"Could not load previous state: {e}")
            return None

    def _detect_session_source(
        self, current_id: str, prev_state: dict[str, Any] | None
    ) -> tuple[str, bool, dict[str, Any]]:
        """
        Detect session source and compaction status.

        Returns:
            (source, is_post_compact, metadata)
            where source is one of: "startup", "resume", "compact", "clear"
        """
        metadata: dict[str, Any] = {}

        # No previous state = startup or fresh session
        if not prev_state:
            return "startup", False, metadata

        prev_id = prev_state.get("session_id")

        # Same session ID = resume (context switch within same Claude session)
        if current_id == prev_id:
            metadata["reason"] = "same_session_id"
            return "resume", False, metadata

        # Different session ID - check if previous was ended
        prev_was_ended = prev_state.get("is_ended", False)

        # Check for compact marker file
        compact_marker = self.sessions_dir / self.COMPACT_MARKER_FILE
        has_compact_marker = compact_marker.exists()

        if has_compact_marker or prev_was_ended:
            # This is post-compact
            metadata["reason"] = "previous_session_ended"
            metadata["previous_session_id"] = prev_id
            metadata["had_compact_marker"] = has_compact_marker
            return "compact", True, metadata

        # Check if this looks like a /clear command
        if self._detect_clear_command():
            metadata["reason"] = "clear_command_detected"
            return "clear", False, metadata

        # Different session ID but previous wasn't ended - likely resume after context switch
        metadata["reason"] = "different_session_id_no_end"
        return "resume", False, metadata

    def _should_enable_delegation(
        self, is_post_compact: bool, prev_state: dict[str, Any] | None
    ) -> bool:
        """
        Determine if delegation should be enabled.

        Returns:
            True if delegation should be active in this session
        """
        # Check environment variable override
        if os.environ.get("HTMLGRAPH_DELEGATION_DISABLE") == "1":
            return False

        # Enable delegation if:
        # 1. This is post-compact (context carry-over needed)
        # 2. Previous session had delegation enabled
        # 3. Features are available to work on
        if is_post_compact:
            return True

        if prev_state:
            if prev_state.get("delegation_enabled", False):
                return True

        # Check if there are features available
        if self._has_available_work():
            return True

        return False

    def _is_session_valid(
        self, session_id: str, prev_state: dict[str, Any] | None
    ) -> bool:
        """
        Check if session is valid for work tracking.

        Returns:
            True if this is a valid session for work
        """
        # Check if session directory exists
        sessions_dir = self.graph_dir / "sessions"
        if not sessions_dir.exists():
            return True  # Valid - directory will be created

        # Check if we can write to sessions directory
        try:
            test_file = sessions_dir / ".test"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            logger.warning("Cannot write to sessions directory")
            return False

    def _detect_clear_command(self) -> bool:
        """
        Detect if /clear command was run (clears .htmlgraph state).

        Returns:
            True if /clear was likely run
        """
        # Check if clear marker exists
        clear_marker = self.graph_dir / ".clear_marker"
        return clear_marker.exists()

    def _has_available_work(self) -> bool:
        """
        Check if there are features available to work on.

        Returns:
            True if there are features in todo or in-progress state
        """
        features_dir = self.graph_dir / "features"
        if not features_dir.exists():
            return False

        try:
            html_files = list(features_dir.glob("*.html"))
            return len(html_files) > 0
        except Exception:
            return False

    @staticmethod
    def _get_git_status() -> dict[str, Any]:
        """Get current git status (for compaction detection)."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {
                "has_changes": bool(result.stdout.strip()),
                "status_output": result.stdout.strip(),
            }
        except Exception:
            return {"has_changes": False, "status_output": ""}
