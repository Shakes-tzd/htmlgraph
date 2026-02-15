"""
Session lifecycle management and error handling.

Provides:
- SessionLifecycleOps: start, end, get, normalize, dedupe sessions
- ErrorManager: log, search, and summarize session errors

Uses SessionConverter for persistence (NOT graph queries).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from htmlgraph.agent_detection import detect_agent_name
from htmlgraph.converter import SessionConverter
from htmlgraph.ids import generate_id
from htmlgraph.models import ActivityEntry, ErrorEntry, Session

if TYPE_CHECKING:
    from htmlgraph.sessions.spikes import SpikeManager

logger = logging.getLogger(__name__)


# =========================================================================
# Session Lifecycle Operations
# =========================================================================


class SessionLifecycleOps:
    """Manages session lifecycle: start, end, get, normalize, dedupe."""

    DEFAULT_SESSION_DEDUPE_WINDOW_SECONDS = 120

    def __init__(
        self,
        session_converter: SessionConverter,
        sessions_dir: Path,
        graph_dir: Path,
        session_dedupe_window_seconds: int = DEFAULT_SESSION_DEDUPE_WINDOW_SECONDS,
    ):
        self.session_converter = session_converter
        self.sessions_dir = sessions_dir
        self.graph_dir = graph_dir
        self.session_dedupe_window_seconds = session_dedupe_window_seconds

        # Cache for active session
        self._active_session: Session | None = None

        # Cache for active sessions list
        self._active_sessions_cache: list[Session] | None = None
        self._sessions_cache_dirty: bool = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def list_active_sessions(self) -> list[Session]:
        """Return all active sessions found on disk (cached)."""
        if self._sessions_cache_dirty or self._active_sessions_cache is None:
            self._active_sessions_cache = [
                s for s in self.session_converter.load_all() if s.status == "active"
            ]
            self._sessions_cache_dirty = False
        return self._active_sessions_cache

    def choose_canonical(self, sessions: list[Session]) -> Session | None:
        """Choose a stable 'canonical' session when multiple are active."""
        if not sessions:
            return None
        sessions.sort(
            key=lambda s: (s.event_count, s.last_activity.timestamp()),
            reverse=True,
        )
        return sessions[0]

    def mark_stale(self, session: Session) -> None:
        """Mark a session as stale."""
        if session.status != "active":
            return
        now = datetime.now(timezone.utc)
        session.status = "stale"
        session.ended_at = now
        session.last_activity = now
        self.session_converter.save(session)
        self._sessions_cache_dirty = True

    def invalidate_cache(self) -> None:
        """Mark the sessions cache as dirty."""
        self._sessions_cache_dirty = True

    @property
    def active_session(self) -> Session | None:
        return self._active_session

    @active_session.setter
    def active_session(self, value: Session | None) -> None:
        self._active_session = value

    # ------------------------------------------------------------------
    # Public lifecycle operations
    # ------------------------------------------------------------------

    def normalize_active_sessions(self) -> dict[str, int]:
        """Keep at most one active non-subagent session per agent."""
        active_sessions = self.list_active_sessions()
        kept = 0
        staled = 0

        by_agent: dict[str, list[Session]] = {}
        for s in active_sessions:
            if s.is_subagent:
                continue
            by_agent.setdefault(s.agent, []).append(s)

        for _agent, sessions in by_agent.items():
            canonical = self.choose_canonical(sessions)
            if not canonical:
                continue
            kept += 1
            for s in sessions:
                if s.id != canonical.id:
                    self.mark_stale(s)
                    staled += 1

        return {"kept": kept, "staled": staled}

    def start_session(
        self,
        session_id: str | None = None,
        agent: str | None = None,
        is_subagent: bool = False,
        continued_from: str | None = None,
        start_commit: str | None = None,
        title: str | None = None,
        parent_session_id: str | None = None,
        get_current_commit: Any = None,
        spikes: SpikeManager | None = None,
    ) -> Session:
        """Start a new session."""
        if agent is None:
            agent = detect_agent_name()

        now = datetime.now()

        if session_id is None:
            session_id = generate_id(node_type="session", title=title or agent)

        desired_commit = start_commit or (
            get_current_commit() if get_current_commit else None
        )

        # Idempotency
        existing = self.session_converter.load(session_id)
        if existing:
            if existing.status != "active":
                existing.status = "active"
            existing.last_activity = now
            if not existing.start_commit:
                existing.start_commit = desired_commit
            if title and not existing.title:
                existing.title = title
            self.session_converter.save(existing)
            self._sessions_cache_dirty = True
            self._active_session = existing
            return existing

        # Dedupe
        if not is_subagent:
            active_sessions = [
                s
                for s in self.list_active_sessions()
                if (not s.is_subagent) and s.agent == agent
            ]
            canonical = self.choose_canonical(active_sessions)
            if canonical and canonical.start_commit == desired_commit:
                self._active_session = canonical
                canonical.last_activity = now
                self.session_converter.save(canonical)
                self._sessions_cache_dirty = True
                return canonical

            for s in active_sessions:
                self.mark_stale(s)

        session = Session(
            id=session_id,
            agent=agent,
            is_subagent=is_subagent,
            continued_from=continued_from,
            start_commit=desired_commit,
            status="active",
            started_at=now,
            last_activity=now,
            title=title or "",
            parent_session=parent_session_id,
        )

        session.add_activity(
            ActivityEntry(
                tool="SessionStart",
                summary="Session started",
                timestamp=now,
            )
        )

        os.environ["HTMLGRAPH_PARENT_SESSION"] = session.id

        self.session_converter.save(session)
        self._sessions_cache_dirty = True
        self._active_session = session

        # Spike management
        if spikes:
            spikes.complete_transition_spikes_on_conversation_start(session.agent)
            spikes.create_session_init_spike(session)

        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        if self._active_session and self._active_session.id == session_id:
            return self._active_session
        return self.session_converter.load(session_id)

    def get_last_ended_session(self, agent: str | None = None) -> Session | None:
        """Get the most recently ended session."""
        sessions = [s for s in self.session_converter.load_all() if s.status == "ended"]
        if agent:
            sessions = [s for s in sessions if s.agent == agent]
        if not sessions:
            return None

        def sort_key(session: Session) -> datetime:
            if session.ended_at:
                return session.ended_at
            if session.last_activity:
                return session.last_activity
            return session.started_at

        sessions.sort(key=sort_key, reverse=True)
        return sessions[0]

    def get_active_session(self, agent: str | None = None) -> Session | None:
        """Get the currently active session."""
        if self._active_session and self._active_session.status == "active":
            if not agent or self._active_session.agent == agent:
                return self._active_session

        sessions = self.list_active_sessions()
        if agent:
            sessions = [s for s in sessions if s.agent == agent]

        canonical = self.choose_canonical(sessions)
        if canonical:
            self._active_session = canonical
            return canonical
        return None

    def get_active_session_for_agent(self, agent: str) -> Session | None:
        """Get the currently active session for a specific agent."""
        if not agent:
            return self.get_active_session()

        if (
            self._active_session
            and self._active_session.status == "active"
            and self._active_session.agent == agent
        ):
            return self._active_session

        sessions = [s for s in self.list_active_sessions() if s.agent == agent]
        canonical = self.choose_canonical(sessions)
        if canonical:
            self._active_session = canonical
            return canonical
        return None

    def end_session(
        self,
        session_id: str,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
        end_commit: str | None = None,
        get_current_commit: Any = None,
        release_session_features: Any = None,
    ) -> Session | None:
        """End a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        if handoff_notes is not None:
            session.handoff_notes = handoff_notes
        if recommended_next is not None:
            session.recommended_next = recommended_next
        if blockers is not None:
            session.blockers = blockers
        if end_commit is not None:
            session.end_commit = end_commit
        elif not session.end_commit:
            session.end_commit = get_current_commit() if get_current_commit else None

        session.end()
        session.add_activity(
            ActivityEntry(
                tool="SessionEnd",
                summary="Session ended",
                timestamp=datetime.now(timezone.utc),
            )
        )

        if release_session_features:
            release_session_features(session_id)

        self.session_converter.save(session)
        self._sessions_cache_dirty = True

        if self._active_session and self._active_session.id == session_id:
            self._active_session = None

        return session

    def set_session_handoff(
        self,
        session_id: str,
        handoff_notes: str | None = None,
        recommended_next: str | None = None,
        blockers: list[str] | None = None,
    ) -> Session | None:
        """Set handoff context on a session without ending it."""
        session = self.get_session(session_id)
        if not session:
            return None

        updated = False
        if handoff_notes is not None:
            session.handoff_notes = handoff_notes
            updated = True
        if recommended_next is not None:
            session.recommended_next = recommended_next
            updated = True
        if blockers is not None:
            session.blockers = blockers
            updated = True

        if updated:
            session.add_activity(
                ActivityEntry(
                    tool="SessionHandoff",
                    summary="Session handoff updated",
                    timestamp=datetime.now(),
                )
            )
            self.session_converter.save(session)

        return session

    def dedupe_orphan_sessions(
        self,
        max_events: int = 1,
        move_dir_name: str = "_orphans",
        dry_run: bool = False,
        stale_extra_active: bool = True,
    ) -> dict[str, int]:
        """Move low-signal sessions out of the main sessions dir."""
        moved = 0
        scanned = 0
        missing = 0

        dest_dir = self.sessions_dir / move_dir_name
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        for session in self.session_converter.load_all():
            scanned += 1
            if session.event_count > max_events:
                continue
            if len(session.activity_log) > max_events:
                continue
            if session.activity_log and session.activity_log[0].tool != "SessionStart":
                continue

            src = self.sessions_dir / f"{session.id}.html"
            if not src.exists():
                missing += 1
                continue

            if not dry_run and session.status == "active":
                self.mark_stale(session)

            if not dry_run:
                src.rename(dest_dir / src.name)

            moved += 1

        normalized = {"kept": 0, "staled": 0}
        if stale_extra_active and not dry_run:
            normalized = self.normalize_active_sessions()

        return {
            "scanned": scanned,
            "moved": moved,
            "missing": missing,
            "kept_active": normalized.get("kept", 0),
            "staled_active": normalized.get("staled", 0),
        }

    def continue_from_last(
        self,
        agent: str | None = None,
        auto_create_session: bool = True,
    ) -> tuple[Session | None, Any]:
        """Continue work from the last completed session."""
        from htmlgraph.sessions.handoff import SessionResume

        class MinimalSDK:
            def __init__(self, directory: Path) -> None:
                self._directory = directory

        sdk: Any = MinimalSDK(self.graph_dir)
        resume = SessionResume(sdk)

        last_session = resume.get_last_session(agent=agent)
        if not last_session:
            return None, None

        resume_info = resume.build_resume_info(last_session)

        new_session = None
        if auto_create_session:
            sid = generate_id("sess")
            new_session = self.start_session(
                session_id=sid,
                agent=agent or last_session.agent,
                title=f"Continuing from {last_session.id}",
            )
            new_session.continued_from = last_session.id
            self.session_converter.save(new_session)

        return new_session, resume_info

    def end_session_with_handoff(
        self,
        session_id: str,
        summary: str | None = None,
        next_focus: str | None = None,
        blockers: list[str] | None = None,
        keep_context: list[str] | None = None,
        auto_recommend_context: bool = True,
        end_session_fn: Any = None,
    ) -> Session | None:
        """End session with handoff information."""
        from htmlgraph.sessions.handoff import ContextRecommender, HandoffBuilder

        session = self.get_session(session_id)
        if not session:
            return None

        builder = HandoffBuilder(session)
        if summary:
            builder.add_summary(summary)
        if next_focus:
            builder.add_next_focus(next_focus)
        if blockers:
            builder.add_blockers(blockers)
        if keep_context:
            builder.add_context_files(keep_context)
        if auto_recommend_context:
            recommender = ContextRecommender()
            builder.auto_recommend_context(recommender, max_files=10)

        handoff_data = builder.build()
        session.handoff_notes = handoff_data["handoff_notes"]
        session.recommended_next = handoff_data["recommended_next"]
        session.blockers = handoff_data["blockers"]
        session.recommended_context = handoff_data["recommended_context"]

        self.session_converter.save(session)

        if end_session_fn:
            end_session_fn(session_id)

        return session

    def ensure_session_for_agent(self, agent: str) -> Session:
        """Ensure there is an active session for agent, creating one if needed."""
        active = self.get_active_session_for_agent(agent)
        if active:
            return active
        return self.start_session(
            session_id=None,
            agent=agent,
            title=f"Auto session ({agent})",
        )


# =========================================================================
# Error Management
# =========================================================================


class ErrorManager:
    """Manages error logging and retrieval for sessions."""

    def __init__(
        self,
        session_converter: SessionConverter,
    ):
        self.session_converter = session_converter

    def _get_session(
        self, session_id: str, cached: Session | None = None
    ) -> Session | None:
        """Get session by ID, using cached version if available."""
        if cached and cached.id == session_id:
            return cached
        return self.session_converter.load(session_id)

    def log_error(
        self,
        session_id: str,
        error: Exception,
        traceback_str: str,
        context: dict[str, Any] | None = None,
        cached_session: Session | None = None,
    ) -> None:
        """
        Log error with full traceback to session.

        Args:
            session_id: Session ID to log error to
            error: The exception object
            traceback_str: Full traceback string
            context: Optional context dict
            cached_session: Optional cached session to avoid disk read
        """
        session = self._get_session(session_id, cached_session)
        if not session:
            return

        error_entry = ErrorEntry(
            timestamp=datetime.now(),
            error_type=error.__class__.__name__,
            message=str(error),
            traceback=traceback_str,
        )

        session.error_log.append(error_entry)
        self.session_converter.save(session)

    def get_session_errors(
        self,
        session_id: str,
        cached_session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all errors logged for a session.

        Args:
            session_id: Session ID
            cached_session: Optional cached session

        Returns:
            List of error records, or empty list if none
        """
        session = self._get_session(session_id, cached_session)
        if not session:
            return []
        return [error.model_dump() for error in session.error_log]

    def search_errors(
        self,
        session_id: str,
        error_type: str | None = None,
        pattern: str | None = None,
        cached_session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search errors in a session by type and/or pattern.

        Args:
            session_id: Session ID to search
            error_type: Filter by exception type (e.g., "ValueError")
            pattern: Regex pattern to match in error message
            cached_session: Optional cached session

        Returns:
            List of matching error records
        """
        session = self._get_session(session_id, cached_session)
        if not session:
            return []

        errors = [error.model_dump() for error in session.error_log]

        if error_type:
            errors = [e for e in errors if e.get("error_type") == error_type]

        if pattern:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            errors = [
                e for e in errors if compiled_pattern.search(e.get("message", ""))
            ]

        return errors

    def get_error_summary(
        self,
        session_id: str,
        cached_session: Session | None = None,
    ) -> dict[str, Any]:
        """
        Get summary statistics of errors in a session.

        Args:
            session_id: Session ID
            cached_session: Optional cached session

        Returns:
            Dictionary with error summary statistics
        """
        session = self._get_session(session_id, cached_session)
        if not session or not session.error_log:
            return {
                "total_errors": 0,
                "error_types": {},
                "first_error": None,
                "last_error": None,
            }

        errors = session.error_log
        error_types: dict[str, int] = {}

        for error in errors:
            etype = error.error_type
            error_types[etype] = error_types.get(etype, 0) + 1

        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "first_error": errors[0].model_dump() if errors else None,
            "last_error": errors[-1].model_dump() if errors else None,
        }
