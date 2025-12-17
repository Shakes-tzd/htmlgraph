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
from typing import Any


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
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
        return path

    def iter_events(self) -> tuple[Path, dict[str, Any]]:
        """
        Yield (path, event_dict) for all events across all JSONL files.
        Skips malformed lines.
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
