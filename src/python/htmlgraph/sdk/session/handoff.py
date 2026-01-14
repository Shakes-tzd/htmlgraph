"""
Session handoff context management for SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.session_manager import SessionManager


class SessionHandoffMixin:
    """
    Provides session handoff operations for cross-session continuity.

    Attributes accessed by mixins:
        session_manager: SessionManager instance
        _agent_id: Agent identifier
    """

    session_manager: SessionManager

    def set_session_handoff(
        self,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """
        Set handoff context on a session.

        Args:
            handoff_notes: Notes for next session/agent
            recommended_next: Suggested next steps
            blockers: List of blockers
            session_id: Specific session ID (defaults to active session)

        Returns:
            Updated Session or None if not found
        """
        if not session_id:
            if self._agent_id:  # type: ignore[attr-defined]
                active = self.session_manager.get_active_session_for_agent(
                    self._agent_id  # type: ignore[attr-defined]
                )
            else:
                active = self.session_manager.get_active_session()
            if not active:
                return None
            session_id = active.id

        return self.session_manager.set_session_handoff(
            session_id=session_id,
            handoff_notes=handoff_notes,
            recommended_next=recommended_next,
            blockers=blockers,
        )

    def end_session_with_handoff(
        self,
        session_id: str | None = None,
        summary: str | None = None,
        next_focus: str | None = None,
        blockers: list[str] | None = None,
        keep_context: list[str] | None = None,
        auto_recommend_context: bool = True,
    ) -> Any:
        """
        End session with handoff information for next session.

        Args:
            session_id: Session to end (None = active session)
            summary: What was accomplished
            next_focus: What should be done next
            blockers: List of blockers
            keep_context: List of files to keep context for
            auto_recommend_context: Auto-recommend files from git

        Returns:
            Updated Session or None

        Example:
            >>> sdk.end_session_with_handoff(
            ...     summary="Completed OAuth integration",
            ...     next_focus="Implement JWT token refresh",
            ...     blockers=["Waiting for security review"],
            ...     keep_context=["src/auth/oauth.py"]
            ... )
        """
        if not session_id:
            if self._agent_id:  # type: ignore[attr-defined]
                active = self.session_manager.get_active_session_for_agent(
                    self._agent_id  # type: ignore[attr-defined]
                )
            else:
                active = self.session_manager.get_active_session()
            if not active:
                return None
            session_id = active.id

        return self.session_manager.end_session_with_handoff(
            session_id=session_id,
            summary=summary,
            next_focus=next_focus,
            blockers=blockers,
            keep_context=keep_context,
            auto_recommend_context=auto_recommend_context,
        )
