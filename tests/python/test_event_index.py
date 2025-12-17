from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from htmlgraph.analytics_index import AnalyticsIndex
from htmlgraph.event_log import EventRecord, JsonlEventLog


def test_jsonl_event_log_append_and_iter(tmp_path: Path):
    log = JsonlEventLog(tmp_path / "events")

    record = EventRecord(
        event_id="s-1",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        session_id="s",
        agent="claude-code",
        tool="Read",
        summary="Read: foo.py",
        success=True,
        feature_id="feature-1",
        drift_score=0.25,
        start_commit="abc123",
        continued_from=None,
        file_paths=["foo.py"],
        payload={"k": "v"},
    )

    log.append(record)

    events = [e for _, e in log.iter_events()]
    assert len(events) == 1
    assert events[0]["event_id"] == "s-1"
    assert events[0]["session_id"] == "s"
    assert events[0]["file_paths"] == ["foo.py"]


def test_analytics_index_rebuild_overview(tmp_path: Path):
    db = AnalyticsIndex(tmp_path / "index.sqlite")

    events = [
        {
            "event_id": "e1",
            "timestamp": "2025-01-01T12:00:00",
            "session_id": "s1",
            "tool": "Read",
            "summary": "Read: a",
            "success": True,
            "feature_id": "f1",
            "drift_score": 0.1,
            "file_paths": ["a.py"],
            "payload": {"x": 1},
        },
        {
            "event_id": "e2",
            "timestamp": "2025-01-01T12:01:00",
            "session_id": "s1",
            "tool": "Bash",
            "summary": "Bash: pytest",
            "success": False,
            "feature_id": "f1",
            "drift_score": 0.9,
            "file_paths": [],
            "payload": None,
        },
    ]

    result = db.rebuild_from_events(events)
    assert result["inserted"] == 2

    overview = db.overview()
    assert overview["events"] == 2
    assert overview["failures"] == 1

    sess_events = db.session_events("s1", limit=10)
    assert len(sess_events) == 2
    assert {e["event_id"] for e in sess_events} == {"e1", "e2"}

