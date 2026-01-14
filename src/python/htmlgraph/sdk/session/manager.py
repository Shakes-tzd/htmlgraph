"""
SessionManager accessor and session creation/validation for SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.session_manager import SessionManager


class SessionManagerMixin:
    """
    Provides SessionManager accessor and session lifecycle operations.

    Attributes accessed by mixins:
        session_manager: SessionManager instance
        _db: HtmlGraphDB instance
        _agent_id: Agent identifier
        _parent_session: Parent session ID (if nested)
    """

    session_manager: SessionManager

    def _ensure_session_exists(
        self, session_id: str, parent_event_id: str | None = None
    ) -> None:
        """
        Create a session record if it doesn't exist.

        Args:
            session_id: Session ID to ensure exists
            parent_event_id: Event that spawned this session (optional)
        """
        if not self._db.connection:  # type: ignore[attr-defined]
            self._db.connect()  # type: ignore[attr-defined]

        cursor = self._db.connection.cursor()  # type: ignore[attr-defined,union-attr]
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
        )
        exists = cursor.fetchone()[0] > 0

        if not exists:
            # Create session record
            self._db.insert_session(  # type: ignore[attr-defined]
                session_id=session_id,
                agent_assigned=self._agent_id,  # type: ignore[attr-defined]
                is_subagent=self._parent_session is not None,  # type: ignore[attr-defined]
                parent_session_id=self._parent_session,  # type: ignore[attr-defined]
                parent_event_id=parent_event_id,
            )

    def start_session(
        self,
        session_id: str | None = None,
        title: str | None = None,
        agent: str | None = None,
    ) -> Any:
        """
        Start a new session.

        Args:
            session_id: Optional session ID
            title: Optional session title
            agent: Optional agent override (defaults to SDK agent)

        Returns:
            New Session instance
        """
        return self.session_manager.start_session(
            session_id=session_id,
            agent=agent or self._agent_id or "cli",  # type: ignore[attr-defined]
            title=title,
            parent_session_id=self._parent_session,  # type: ignore[attr-defined]
        )

    def end_session(
        self,
        session_id: str,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
    ) -> Any:
        """
        End a session.

        Args:
            session_id: Session ID to end
            handoff_notes: Optional handoff notes
            recommended_next: Optional recommendations
            blockers: Optional blockers

        Returns:
            Ended Session instance
        """
        return self.session_manager.end_session(
            session_id=session_id,
            handoff_notes=handoff_notes,
            recommended_next=recommended_next,
            blockers=blockers,
        )
