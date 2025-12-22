"""
Event logging for HtmlGraph.

This module provides a Git-friendly append-only JSONL event log.

Design goals:
- Source of truth lives in the filesystem (and therefore Git)
- Append-only writes for high-frequency activity events
- Deterministic serialization for rebuildable analytics indexes
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import WorkType


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    timestamp: datetime
    session_id: str
    agent: str
    tool: str
    summary: str
    success: bool
    feature_id: str | None
    drift_score: float | None
    start_commit: str | None
    continued_from: str | None
    work_type: str | None = None  # WorkType enum value
    session_status: str | None = None
    file_paths: list[str] | None = None
    payload: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "agent": self.agent,
            "tool": self.tool,
            "summary": self.summary,
            "success": self.success,
            "feature_id": self.feature_id,
            "work_type": self.work_type,
            "drift_score": self.drift_score,
            "start_commit": self.start_commit,
            "continued_from": self.continued_from,
            "session_status": self.session_status,
            "file_paths": self.file_paths or [],
            "payload": self.payload,
        }


class JsonlEventLog:
    """
    Append-only JSONL event log stored under `.htmlgraph/events/`.
    """

    def __init__(self, events_dir: Path | str):
        self.events_dir = Path(events_dir)
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def path_for_session(self, session_id: str) -> Path:
        # Keep simple and filesystem-friendly.
        return self.events_dir / f"{session_id}.jsonl"

    def append(self, record: EventRecord) -> Path:
        path = self.path_for_session(record.session_id)
        line = json.dumps(record.to_json(), ensure_ascii=False, default=str) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)

        # Best-effort dedupe: some producers (e.g. git hooks) may retry or be chained.
        # Event IDs are intended to be unique; if we already have this ID in the
        # existing file tail, skip appending.
        try:
            if path.exists():
                with path.open("rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    tail_size = min(size, 64 * 1024)
                    if tail_size:
                        f.seek(-tail_size, 2)
                        tail = f.read(tail_size).decode("utf-8", errors="ignore")
                        for raw in tail.splitlines()[-250:]:
                            raw = raw.strip()
                            if not raw:
                                continue
                            try:
                                existing = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            if existing.get("event_id") == record.event_id:
                                return path
        except Exception:
            pass

        with path.open("a", encoding="utf-8") as f:
            f.write(line)
        return path

    def iter_events(self):
        """
        Yield (path, event_dict) for all events across all JSONL files.
        Skips malformed lines.

        Yields:
            tuple[Path, dict[str, Any]]: Path and event dictionary
        """
        for path in sorted(self.events_dir.glob("*.jsonl")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield path, json.loads(line)
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue

    def get_session_events(
        self,
        session_id: str,
        limit: int | None = None,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get events for a specific session with pagination.

        Args:
            session_id: Session ID to query
            limit: Maximum number of events to return (None = all)
            offset: Number of events to skip from the start

        Returns:
            List of event dictionaries, oldest first
        """
        path = self.path_for_session(session_id)
        if not path.exists():
            return []

        events = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []

        # Apply offset and limit
        if offset > 0:
            events = events[offset:]
        if limit is not None:
            events = events[:limit]

        return events

    def query_events(
        self,
        session_id: str | None = None,
        tool: str | None = None,
        feature_id: str | None = None,
        since: Any = None,  # datetime or ISO string
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Query events with filters.

        Args:
            session_id: Filter by session ID (None = all sessions)
            tool: Filter by tool name (e.g., 'Bash', 'Edit')
            feature_id: Filter by attributed feature ID
            since: Only events after this timestamp (datetime or ISO string)
            limit: Maximum number of events to return

        Returns:
            List of matching event dictionaries, newest first
        """
        from datetime import datetime

        # Convert since to datetime if needed
        since_dt = None
        if since:
            if isinstance(since, str):
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            else:
                since_dt = since

        # Get events from specific session or all sessions
        events: list[dict[str, Any]] = []
        if session_id:
            events = self.get_session_events(session_id, limit=None)
        else:
            events = [evt for _, evt in self.iter_events()]

        # Apply filters
        filtered: list[dict[str, Any]] = []
        for evt in events:
            # Tool filter
            if tool and evt.get('tool') != tool:
                continue

            # Feature filter
            if feature_id and evt.get('feature_id') != feature_id:
                continue

            # Timestamp filter
            if since_dt:
                evt_time_str = evt.get('timestamp')
                if evt_time_str and isinstance(evt_time_str, str):
                    try:
                        evt_time = datetime.fromisoformat(evt_time_str.replace('Z', '+00:00'))
                        if evt_time < since_dt:
                            continue
                    except (ValueError, AttributeError):
                        continue

            filtered.append(evt)

        # Sort newest first and apply limit
        filtered.reverse()
        if limit is not None:
            filtered = filtered[:limit]

        return filtered
