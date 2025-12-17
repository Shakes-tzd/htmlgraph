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


def test_jsonl_event_log_dedupes_duplicate_event_id(tmp_path: Path):
    log = JsonlEventLog(tmp_path / "events")

    record = EventRecord(
        event_id="dup-1",
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
        session_id="s",
        agent="claude-code",
        tool="GitCommit",
        summary="Commit abc",
        success=True,
        feature_id="feature-1",
        drift_score=None,
        start_commit=None,
        continued_from=None,
        file_paths=[],
        payload={"type": "GitCommit"},
    )

    log.append(record)
    # Duplicate ID should be ignored even if timestamp differs.
    log.append(
        EventRecord(
            event_id="dup-1",
            timestamp=datetime(2025, 1, 1, 12, 0, 1),
            session_id="s",
            agent="claude-code",
            tool="GitCommit",
            summary="Commit abc (retry)",
            success=True,
            feature_id="feature-1",
            drift_score=None,
            start_commit=None,
            continued_from=None,
            file_paths=[],
            payload={"type": "GitCommit"},
        )
    )

    path = (tmp_path / "events" / "s.jsonl")
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1


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


def test_analytics_index_rebuild_supports_legacy_git_hook_events(tmp_path: Path):
    db = AnalyticsIndex(tmp_path / "index.sqlite")

    legacy = [
        {
            "type": "GitCommit",
            "timestamp": "2025-01-01T12:00:00",
            "commit_hash": "abc",
            "commit_hash_short": "abc",
            "commit_message": "feat: x\n\nImplements: feature-1",
            "files_changed": ["a.py"],
            "features": ["feature-1"],
            "session_id": "s1",
        }
    ]

    result = db.rebuild_from_events(legacy)
    assert result["inserted"] == 1

    overview = db.overview()
    assert overview["events"] == 1

    sess_events = db.session_events("s1", limit=10)
    assert len(sess_events) == 1
    assert sess_events[0]["tool"] == "GitCommit"
    assert sess_events[0]["feature_id"] == "feature-1"


def test_analytics_index_git_commit_tables(tmp_path: Path):
    db = AnalyticsIndex(tmp_path / "index.sqlite")

    events = [
        {
            "event_id": "git-commit-abc-feature-1",
            "timestamp": "2025-01-01T12:00:00",
            "session_id": "s1",
            "agent": "git",
            "tool": "GitCommit",
            "summary": "Commit abc: feat: x [feature-1]",
            "success": True,
            "feature_id": "feature-1",
            "drift_score": None,
            "file_paths": ["a.py"],
            "payload": {
                "type": "GitCommit",
                "commit_hash": "abc",
                "commit_hash_short": "abc",
                "parents": ["p1", "p2"],
                "is_merge": True,
                "branch": "main",
                "author_name": "A",
                "author_email": "a@example.com",
                "commit_message": "feat: x",
                "subject": "feat: x",
                "files_changed": ["a.py"],
                "insertions": 1,
                "deletions": 0,
                "features": ["feature-1"],
            },
        }
    ]

    result = db.rebuild_from_events(events)
    assert result["inserted"] == 1

    commits = db.feature_commits("feature-1", limit=10)
    assert len(commits) == 1
    assert commits[0]["commit_hash"] == "abc"
    assert commits[0]["parent_count"] == 2

    graph = db.feature_commit_graph("feature-1", limit=10)
    assert "nodes" in graph and "edges" in graph


def test_analytics_index_schema_mismatch_resets(tmp_path: Path):
    # Create a DB with a bogus schema version and ensure we don't error.
    import sqlite3

    path = tmp_path / "index.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO meta(key,value) VALUES('schema_version', '999')")

    db = AnalyticsIndex(path)
    overview = db.overview()
    assert "events" in overview
