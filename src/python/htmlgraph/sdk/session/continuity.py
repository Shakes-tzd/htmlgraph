"""
Session continuity and resume operations for SDK.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.session_manager import SessionManager


class SessionContinuityMixin:
    """
    Provides session continuity operations for resuming work.

    Attributes accessed by mixins:
        session_manager: SessionManager instance
        _agent_id: Agent identifier
    """

    session_manager: SessionManager

    def continue_from_last(
        self,
        agent: str | None = None,
        auto_create_session: bool = True,
    ) -> tuple[Any, Any]:
        """
        Continue work from the last completed session.

        Loads context from previous session including handoff notes,
        recommended files, blockers, and recent commits.

        Args:
            agent: Filter by agent (None = current SDK agent)
            auto_create_session: Create new session if True

        Returns:
            Tuple of (new_session, resume_info) or (None, None)

        Example:
            >>> sdk = SDK(agent="claude")
            >>> session, resume = sdk.continue_from_last()
            >>> if resume:
            ...     logger.info("%s", resume.summary)
            ...     logger.info("%s", resume.next_focus)
            ...     for file in resume.recommended_files:
            ...         logger.info(f"  - {file}")
        """
        if not agent:
            agent = self._agent_id  # type: ignore[attr-defined]

        return self.session_manager.continue_from_last(
            agent=agent,
            auto_create_session=auto_create_session,
        )
