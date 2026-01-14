from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
SessionCollection - Session state and management interface.

Provides methods to:
- Get current session state automatically
- Set up environment variables automatically
- Track session metadata
- Detect post-compact sessions

Integration with SessionStart hook:
    sdk = SDK()
    state = sdk.sessions.get_current_state()
    sdk.sessions.setup_environment_variables(state)
"""


from typing import TYPE_CHECKING

from htmlgraph.collections.base import BaseCollection
from htmlgraph.session_state import SessionState, SessionStateManager

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


class SessionCollection(BaseCollection):
    """
    Collection interface for session state management.

    Extends BaseCollection with session-specific state management operations.

    Provides:
    - Automatic session state detection (post-compact, delegation status)
    - Environment variable setup (CLAUDE_SESSION_ID, CLAUDE_DELEGATION_ENABLED, etc.)
    - Session metadata recording and retrieval
    - Compact detection

    Example:
        >>> sdk = SDK(agent="claude")
        >>> state = sdk.sessions.get_current_state()
        >>> sdk.sessions.setup_environment_variables(state)
        # All environment variables automatically set
    """

    _collection_name = "sessions"
    _node_type = "session"

    def __init__(self, sdk: SDK):
        """
        Initialize SessionCollection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "sessions", "session")
        self._state_manager = SessionStateManager(sdk._directory)

    def get_current_state(self) -> SessionState:
        """
        Get current session state with automatic detection.

        Automatically detects:
        - Current session ID
        - Session source (startup, resume, compact, clear)
        - Post-compact status
        - Delegation enable/disable
        - Session validity

        Returns:
            SessionState dict with:
            - session_id: Current session identifier
            - session_source: "startup", "resume", "compact", "clear"
            - is_post_compact: True if this is post-compact session
            - previous_session_id: Previous session ID if available
            - delegation_enabled: Should delegation be active
            - prompt_injected: Was orchestrator prompt injected
            - session_valid: Is session valid for tracking
            - timestamp: Current UTC timestamp
            - compact_metadata: Compact detection details

        Example:
            >>> sdk = SDK()
            >>> state = sdk.sessions.get_current_state()
            >>> logger.info(f"Session: {state['session_id']}")
            >>> logger.info(f"Post-compact: {state['is_post_compact']}")
            >>> logger.info(f"Delegation enabled: {state['delegation_enabled']}")
        """
        return self._state_manager.get_current_state()

    def setup_environment_variables(
        self,
        session_state: SessionState | None = None,
        auto_detect_compact: bool = True,
    ) -> dict[str, str]:
        """
        Automatically set up environment variables for session state.

        Sets up environment variables that persist across context boundaries:
        - CLAUDE_SESSION_ID: Current session identifier
        - CLAUDE_SESSION_SOURCE: "startup|resume|compact|clear"
        - CLAUDE_SESSION_COMPACTED: "true|false"
        - CLAUDE_DELEGATION_ENABLED: "true|false"
        - CLAUDE_PREVIOUS_SESSION_ID: Previous session ID
        - CLAUDE_ORCHESTRATOR_ACTIVE: "true|false"
        - CLAUDE_PROMPT_PERSISTENCE_VERSION: "1.0"

        Args:
            session_state: Session state dict (auto-detected if not provided)
            auto_detect_compact: Whether to auto-detect post-compact state

        Returns:
            Dict of environment variables that were set

        Example:
            >>> sdk = SDK()
            >>> state = sdk.sessions.get_current_state()
            >>> env_vars = sdk.sessions.setup_environment_variables(state)
            >>> logger.info(f"CLAUDE_SESSION_ID: {env_vars['CLAUDE_SESSION_ID']}")
            >>> logger.info(f"CLAUDE_DELEGATION_ENABLED: {env_vars['CLAUDE_DELEGATION_ENABLED']}")
        """
        return self._state_manager.setup_environment_variables(
            session_state=session_state, auto_detect_compact=auto_detect_compact
        )

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

        Example:
            >>> sdk = SDK()
            >>> sdk.sessions.record_state(
            ...     session_id="sess-123",
            ...     source="compact",
            ...     is_post_compact=True,
            ...     delegation_enabled=True
            ... )
        """
        self._state_manager.record_state(
            session_id=session_id,
            source=source,
            is_post_compact=is_post_compact,
            delegation_enabled=delegation_enabled,
            environment_vars=environment_vars,
        )

    def detect_compact_automatically(self) -> bool:
        """
        Auto-detect if this is post-compact by comparing session IDs.

        Returns:
            True if this is a post-compact session

        Example:
            >>> sdk = SDK()
            >>> if sdk.sessions.detect_compact_automatically():
            ...     logger.info("This is a post-compact session")
        """
        return self._state_manager.detect_compact_automatically()

    def get_state_manager(self) -> SessionStateManager:
        """
        Get the underlying SessionStateManager.

        Use this for advanced session state operations.

        Returns:
            SessionStateManager instance

        Example:
            >>> sdk = SDK()
            >>> manager = sdk.sessions.get_state_manager()
            >>> state = manager.get_current_state()
        """
        return self._state_manager
