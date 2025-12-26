from __future__ import annotations

import subprocess
from pathlib import Path

from htmlgraph.event_log import JsonlEventLog
from htmlgraph.git_events import log_git_commit, parse_feature_refs
from htmlgraph.session_manager import SessionManager


def _run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True).strip()


def test_parse_feature_refs():
    msg = "feat: x\n\nImplements: feature-abc\nFixes: bug-123\nRefs: feature-abc\nAlso mentions feature-xyz."
    refs = parse_feature_refs(msg)
    assert "feature-abc" in refs
    assert "bug-123" in refs
    assert "feature-xyz" in refs


def test_log_git_commit_writes_event_record(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.name", "Test User"], cwd=repo)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    _run(["git", "config", "commit.gpgsign", "false"], cwd=repo)

    # Start an HtmlGraph session so git events attach to a real session_id.
    graph_dir = repo / ".htmlgraph"
    manager = SessionManager(graph_dir)
    manager.start_session(session_id="session-1", agent="test", title="t")

    (repo / "a.txt").write_text("hello")
    _run(["git", "add", "a.txt"], cwd=repo)
    _run(["git", "commit", "-m", "feat: x", "-m", "Implements: feature-1"], cwd=repo)

    monkeypatch.chdir(repo)
    assert log_git_commit(graph_dir=".htmlgraph") is True

    log = JsonlEventLog(graph_dir / "events")
    events = [e for _, e in log.iter_events() if e.get("tool") == "GitCommit"]

    # At least one commit event should be written; feature attribution yields per-feature events.
    assert events
    assert any(e.get("feature_id") == "feature-1" for e in events)
    assert all("payload" in e for e in events)
