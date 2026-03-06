"""Tests for the OpenCode session ingester."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from htmlgraph.ingest.opencode import (
    OpenCodeMessage,
    OpenCodeSession,
    IngestResult,
    find_opencode_sessions,
    parse_opencode_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_json(
    session_id: str = "ses_test123",
    project_id: str = "abc123def456",
    directory: str = "/Users/test/myproject",
    title: str = "Test session title",
    created_ms: int = 1767380654720,
    updated_ms: int = 1767384126658,
    version: str = "1.0.223",
    additions: int = 10,
    deletions: int = 2,
    files: int = 3,
) -> dict:
    return {
        "id": session_id,
        "version": version,
        "projectID": project_id,
        "directory": directory,
        "title": title,
        "time": {
            "created": created_ms,
            "updated": updated_ms,
        },
        "summary": {
            "additions": additions,
            "deletions": deletions,
            "files": files,
        },
    }


def _make_message_json(
    msg_id: str = "msg_abc123",
    session_id: str = "ses_test123",
    role: str = "user",
    created_ms: int = 1767380660000,
    agent: str = "build",
    provider_id: str = "opencode",
    model_id: str = "claude-3-5-sonnet",
) -> dict:
    return {
        "id": msg_id,
        "sessionID": session_id,
        "role": role,
        "time": {"created": created_ms},
        "agent": agent,
        "model": {
            "providerID": provider_id,
            "modelID": model_id,
        },
    }


@pytest.fixture
def tmp_opencode_dir(tmp_path: Path) -> Path:
    """Create a temporary OpenCode storage structure with one session."""
    project_id = "abc123def456"
    session_id = "ses_test123"

    session_dir = tmp_path / "session" / project_id
    session_dir.mkdir(parents=True)

    session_data = _make_session_json(session_id=session_id, project_id=project_id)
    (session_dir / f"{session_id}.json").write_text(
        json.dumps(session_data), encoding="utf-8"
    )

    # Write messages
    msg_dir = tmp_path / "message" / session_id
    msg_dir.mkdir(parents=True)
    for i, role in enumerate(["user", "assistant"]):
        msg_data = _make_message_json(
            msg_id=f"msg_{i:04d}",
            session_id=session_id,
            role=role,
            created_ms=1767380660000 + i * 5000,
        )
        (msg_dir / f"msg_{i:04d}.json").write_text(
            json.dumps(msg_data), encoding="utf-8"
        )

    return tmp_path


@pytest.fixture
def tmp_opencode_dir_multi(tmp_path: Path) -> Path:
    """Create a temporary OpenCode storage with multiple projects and sessions."""
    for i in range(2):
        project_id = f"project{i:020d}"
        session_dir = tmp_path / "session" / project_id
        session_dir.mkdir(parents=True)
        for j in range(3):
            sid = f"ses_proj{i}_sess{j}"
            data = _make_session_json(
                session_id=sid,
                project_id=project_id,
                created_ms=1767380654720 + (i * 10 + j) * 1000,
                updated_ms=1767380654720 + (i * 10 + j) * 1000 + 500,
            )
            (session_dir / f"{sid}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )
    return tmp_path


# ---------------------------------------------------------------------------
# OpenCodeMessage tests
# ---------------------------------------------------------------------------


class TestOpenCodeMessage:
    def test_parse_user_message(self) -> None:
        data = _make_message_json(role="user", model_id="claude-3-5-sonnet")
        msg = OpenCodeMessage.from_dict(data)
        assert msg.role == "user"
        assert msg.model_id == "claude-3-5-sonnet"
        assert msg.provider_id == "opencode"
        assert msg.agent == "build"

    def test_parse_assistant_message(self) -> None:
        data = _make_message_json(role="assistant", model_id="gemini-3-pro")
        msg = OpenCodeMessage.from_dict(data)
        assert msg.role == "assistant"
        assert msg.model_id == "gemini-3-pro"

    def test_timestamp_from_ms(self) -> None:
        data = _make_message_json(created_ms=1767380660000)
        msg = OpenCodeMessage.from_dict(data)
        assert msg.created_at.tzinfo is not None
        assert msg.created_at.year >= 2025

    def test_invalid_timestamp_falls_back(self) -> None:
        # Use a value so large it causes OSError on some platforms,
        # or simply verify that a missing time key falls back gracefully.
        data = _make_message_json()
        data["time"] = {}  # missing "created" key → 0 ms → epoch, not now
        msg = OpenCodeMessage.from_dict(data)
        # epoch-based fallback: year should be 1970
        assert msg.created_at.year == 1970

    def test_missing_model_becomes_none(self) -> None:
        data = {
            "id": "msg_x",
            "sessionID": "ses_y",
            "role": "user",
            "time": {"created": 1767380660000},
        }
        msg = OpenCodeMessage.from_dict(data)
        assert msg.model_id is None
        assert msg.provider_id is None
        assert msg.agent is None


# ---------------------------------------------------------------------------
# OpenCodeSession tests
# ---------------------------------------------------------------------------


class TestOpenCodeSession:
    def test_parse_full_session(self, tmp_path: Path) -> None:
        data = _make_session_json()
        sf = tmp_path / "ses_test123.json"
        sf.write_text(json.dumps(data), encoding="utf-8")
        session = OpenCodeSession.from_dict(data, source_file=sf)

        assert session.session_id == "ses_test123"
        assert session.project_id == "abc123def456"
        assert session.directory == "/Users/test/myproject"
        assert session.title == "Test session title"
        assert session.files_changed == 3
        assert session.additions == 10
        assert session.deletions == 2

    def test_user_turn_count(self, tmp_path: Path) -> None:
        data = _make_session_json()
        msgs = [
            OpenCodeMessage.from_dict(_make_message_json(msg_id="m1", role="user")),
            OpenCodeMessage.from_dict(_make_message_json(msg_id="m2", role="assistant")),
            OpenCodeMessage.from_dict(_make_message_json(msg_id="m3", role="user")),
        ]
        session = OpenCodeSession.from_dict(
            data, source_file=tmp_path / "s.json", messages=msgs
        )
        assert session.user_turn_count == 2
        assert session.assistant_turn_count == 1

    def test_models_used_deduped(self, tmp_path: Path) -> None:
        data = _make_session_json()
        msgs = [
            OpenCodeMessage.from_dict(
                _make_message_json(msg_id="m1", role="user", model_id="model-a")
            ),
            OpenCodeMessage.from_dict(
                _make_message_json(msg_id="m2", role="assistant", model_id="model-a")
            ),
            OpenCodeMessage.from_dict(
                _make_message_json(msg_id="m3", role="assistant", model_id="model-b")
            ),
        ]
        session = OpenCodeSession.from_dict(
            data, source_file=tmp_path / "s.json", messages=msgs
        )
        assert session.models_used == ["model-a", "model-b"]

    def test_first_user_prompt_from_title(self, tmp_path: Path) -> None:
        data = _make_session_json(title="My cool session")
        session = OpenCodeSession.from_dict(data, source_file=tmp_path / "s.json")
        assert session.first_user_prompt == "My cool session"

    def test_first_user_prompt_truncated(self, tmp_path: Path) -> None:
        long_title = "x" * 300
        data = _make_session_json(title=long_title)
        session = OpenCodeSession.from_dict(data, source_file=tmp_path / "s.json")
        assert session.first_user_prompt is not None
        assert len(session.first_user_prompt) <= 200

    def test_empty_title_returns_none(self, tmp_path: Path) -> None:
        data = _make_session_json(title="")
        session = OpenCodeSession.from_dict(data, source_file=tmp_path / "s.json")
        assert session.first_user_prompt is None

    def test_timestamps_parsed(self, tmp_path: Path) -> None:
        data = _make_session_json(created_ms=1767380654720, updated_ms=1767384126658)
        session = OpenCodeSession.from_dict(data, source_file=tmp_path / "s.json")
        assert session.created_at.tzinfo is not None
        assert session.updated_at >= session.created_at


# ---------------------------------------------------------------------------
# find_opencode_sessions tests
# ---------------------------------------------------------------------------


class TestFindOpenCodeSessions:
    def test_finds_session_files(self, tmp_opencode_dir: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir)
        assert len(files) == 1
        assert files[0].suffix == ".json"

    def test_finds_multiple_sessions(self, tmp_opencode_dir_multi: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir_multi)
        assert len(files) == 6

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_path)
        assert files == []

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_path / "does-not-exist")
        assert files == []

    def test_returns_sorted_by_mtime_newest_first(
        self, tmp_opencode_dir_multi: Path
    ) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir_multi)
        mtimes = [f.stat().st_mtime for f in files]
        assert mtimes == sorted(mtimes, reverse=True)


# ---------------------------------------------------------------------------
# parse_opencode_session tests
# ---------------------------------------------------------------------------


class TestParseOpenCodeSession:
    def test_parses_valid_session(self, tmp_opencode_dir: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir)
        assert len(files) == 1
        session = parse_opencode_session(files[0])
        assert session is not None
        assert session.session_id == "ses_test123"

    def test_loads_messages_when_present(self, tmp_opencode_dir: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir)
        session = parse_opencode_session(files[0], load_messages=True)
        assert session is not None
        assert len(session.messages) == 2

    def test_skip_messages_when_disabled(self, tmp_opencode_dir: Path) -> None:
        files = find_opencode_sessions(base_path=tmp_opencode_dir)
        session = parse_opencode_session(files[0], load_messages=False)
        assert session is not None
        assert session.messages == []

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "session" / "proj"
        session_dir.mkdir(parents=True)
        bad_file = session_dir / "ses_bad.json"
        bad_file.write_text("{ not valid json }", encoding="utf-8")
        result = parse_opencode_session(bad_file)
        assert result is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        result = parse_opencode_session(tmp_path / "nonexistent.json")
        assert result is None

    def test_parses_session_without_summary(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "session" / "proj"
        session_dir.mkdir(parents=True)
        data = {
            "id": "ses_nosummary",
            "projectID": "proj",
            "directory": "/tmp",
            "title": "No summary",
            "time": {"created": 1767380654720, "updated": 1767380654720},
        }
        sf = session_dir / "ses_nosummary.json"
        sf.write_text(json.dumps(data), encoding="utf-8")
        session = parse_opencode_session(sf, load_messages=False)
        assert session is not None
        assert session.files_changed == 0
        assert session.additions == 0


# ---------------------------------------------------------------------------
# IngestResult tests
# ---------------------------------------------------------------------------


class TestOpenCodeIngestResult:
    def test_default_values(self) -> None:
        result = IngestResult()
        assert result.ingested == 0
        assert result.skipped == 0
        assert result.errors == 0
        assert result.session_ids == []
        assert result.error_files == []
