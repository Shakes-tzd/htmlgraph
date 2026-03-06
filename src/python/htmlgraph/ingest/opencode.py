from __future__ import annotations

"""OpenCode Session Ingester.

Reads OpenCode session files from ~/.local/share/opencode/storage/session/
and message files from ~/.local/share/opencode/storage/message/, parses
conversation turns, and creates HtmlGraph session HTML files.

OpenCode stores data in a two-level storage layout:
    ~/.local/share/opencode/storage/session/<project-id>/<session-id>.json
    ~/.local/share/opencode/storage/message/<session-id>/<message-id>.json

Session JSON structure:
    {
        "id": "<session-id>",
        "version": "<opencode-version>",
        "projectID": "<project-sha>",
        "directory": "/path/to/project",
        "title": "Session title",
        "time": {
            "created": <unix-ms>,
            "updated": <unix-ms>
        },
        "summary": {
            "additions": <int>,
            "deletions": <int>,
            "files": <int>
        }
    }

Message JSON structure:
    {
        "id": "<message-id>",
        "sessionID": "<session-id>",
        "role": "user" | "assistant",
        "time": {
            "created": <unix-ms>
        },
        "agent": "<agent-name>",
        "model": {
            "providerID": "<provider>",
            "modelID": "<model-name>"
        }
    }
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default OpenCode session storage locations (checked in order)
_OPENCODE_DEFAULT_PATHS = [
    Path.home() / ".local" / "share" / "opencode" / "storage",
    Path.home() / ".config" / "opencode" / "storage",
]


@dataclass
class OpenCodeMessage:
    """A single message from an OpenCode session."""

    id: str
    session_id: str
    role: str  # "user" | "assistant"
    created_at: datetime
    agent: str | None = None
    provider_id: str | None = None
    model_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenCodeMessage:
        """Parse a message dict from an OpenCode message JSON file."""
        created_ms = data.get("time", {}).get("created", 0)
        try:
            created_at = datetime.fromtimestamp(created_ms / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            created_at = datetime.now(tz=timezone.utc)

        model_data = data.get("model") or {}

        return cls(
            id=data.get("id", ""),
            session_id=data.get("sessionID", ""),
            role=data.get("role", "unknown"),
            created_at=created_at,
            agent=data.get("agent") or None,
            provider_id=model_data.get("providerID") or None,
            model_id=model_data.get("modelID") or None,
        )


@dataclass
class OpenCodeSession:
    """Parsed representation of an OpenCode session."""

    session_id: str
    project_id: str
    directory: str
    title: str
    created_at: datetime
    updated_at: datetime
    opencode_version: str
    additions: int
    deletions: int
    files_changed: int
    messages: list[OpenCodeMessage]
    source_file: Path

    @property
    def user_turn_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "user")

    @property
    def assistant_turn_count(self) -> int:
        return sum(1 for m in self.messages if m.role == "assistant")

    @property
    def first_user_prompt(self) -> str | None:
        """Return a preview of the title (OpenCode stores titles not raw prompts)."""
        if self.title:
            return self.title[:200]
        return None

    @property
    def models_used(self) -> list[str]:
        """Return deduplicated list of model IDs used in this session."""
        seen: list[str] = []
        for m in self.messages:
            name = m.model_id or ""
            if name and name not in seen:
                seen.append(name)
        return seen

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        source_file: Path,
        messages: list[OpenCodeMessage] | None = None,
    ) -> OpenCodeSession:
        """Parse a full OpenCode session JSON file."""
        time_data = data.get("time", {})
        created_ms = time_data.get("created", 0)
        updated_ms = time_data.get("updated", created_ms)

        try:
            created_at = datetime.fromtimestamp(created_ms / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            created_at = datetime.now(tz=timezone.utc)

        try:
            updated_at = datetime.fromtimestamp(updated_ms / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            updated_at = created_at

        summary = data.get("summary") or {}

        return cls(
            session_id=data.get("id", ""),
            project_id=data.get("projectID", ""),
            directory=data.get("directory", ""),
            title=data.get("title", ""),
            created_at=created_at,
            updated_at=updated_at,
            opencode_version=data.get("version", ""),
            additions=summary.get("additions", 0),
            deletions=summary.get("deletions", 0),
            files_changed=summary.get("files", 0),
            messages=messages or [],
            source_file=source_file,
        )


def find_opencode_sessions(
    base_path: Path | None = None,
    project_dir: Path | str | None = None,
) -> list[Path]:
    """Find all OpenCode session JSON files.

    Searches the OpenCode storage directory for session JSON files.
    The structure is: <base_path>/session/<project-id>/<session-id>.json

    Args:
        base_path: Path to opencode storage root. If None, checks default locations.
        project_dir: If provided, only return sessions for this project directory.
                     Used to filter sessions by matching directory field.

    Returns:
        List of paths to session JSON files, sorted by modification time (newest first).
    """
    search_paths: list[Path] = []

    if base_path is not None:
        search_paths = [Path(base_path)]
    else:
        for candidate in _OPENCODE_DEFAULT_PATHS:
            if candidate.exists():
                search_paths.append(candidate)

    if not search_paths:
        logger.debug("No OpenCode storage directories found")
        return []

    session_files: list[Path] = []
    for search_path in search_paths:
        session_root = search_path / "session"
        if not session_root.exists():
            continue
        # Pattern: <session_root>/<project-id>/<session-id>.json
        for session_file in session_root.glob("*/*.json"):
            session_files.append(session_file)

    # Sort by modification time, newest first
    session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return session_files


def _load_messages_for_session(
    storage_path: Path, session_id: str
) -> list[OpenCodeMessage]:
    """Load all message files for a given session ID.

    Args:
        storage_path: Root of opencode storage (contains session/ and message/).
        session_id: The OpenCode session ID.

    Returns:
        List of OpenCodeMessage objects sorted by creation time.
    """
    message_dir = storage_path / "message" / session_id
    if not message_dir.exists():
        return []

    messages: list[OpenCodeMessage] = []
    for msg_file in message_dir.glob("*.json"):
        try:
            with open(msg_file, encoding="utf-8") as f:
                data = json.load(f)
            messages.append(OpenCodeMessage.from_dict(data))
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.debug("Failed to parse OpenCode message %s: %s", msg_file, e)

    messages.sort(key=lambda m: m.created_at)
    return messages


def parse_opencode_session(
    session_file: Path,
    load_messages: bool = True,
) -> OpenCodeSession | None:
    """Parse a single OpenCode session JSON file.

    Args:
        session_file: Path to the session JSON file.
        load_messages: Whether to load associated message files (default: True).

    Returns:
        Parsed OpenCodeSession, or None if parsing fails.
    """
    try:
        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse OpenCode session %s: %s", session_file, e)
        return None

    messages: list[OpenCodeMessage] = []
    if load_messages:
        # storage root is two levels up from session file:
        # <storage>/session/<project-id>/<session-id>.json
        storage_root = session_file.parent.parent.parent
        session_id = data.get("id", "")
        if session_id:
            messages = _load_messages_for_session(storage_root, session_id)

    try:
        return OpenCodeSession.from_dict(
            data, source_file=session_file, messages=messages
        )
    except Exception as e:
        logger.warning(
            "Failed to construct OpenCodeSession from %s: %s", session_file, e
        )
        return None


@dataclass
class IngestResult:
    """Result of ingesting OpenCode sessions into HtmlGraph."""

    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    session_ids: list[str] = field(default_factory=list)
    error_files: list[str] = field(default_factory=list)


def ingest_opencode_sessions(
    graph_dir: str | Path | None = None,
    agent: str = "opencode",
    base_path: Path | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest OpenCode sessions into HtmlGraph.

    Discovers OpenCode session files, parses them, and creates corresponding
    HtmlGraph session records. Sessions are identified by their OpenCode session ID
    and are idempotent - re-ingesting the same session will update it.

    Args:
        graph_dir: Path to .htmlgraph directory. Auto-discovered if None.
        agent: Agent name to attribute sessions to (default: "opencode").
        base_path: Override for OpenCode storage root. If None, uses defaults.
        limit: Maximum number of sessions to ingest. If None, ingest all.
        dry_run: If True, parse and report but do not write to HtmlGraph.

    Returns:
        IngestResult with counts of ingested, skipped, and errored sessions.
    """
    from htmlgraph import SDK

    result = IngestResult()

    # Find session files
    session_files = find_opencode_sessions(base_path=base_path)
    if not session_files:
        logger.info("No OpenCode session files found")
        return result

    if limit is not None:
        session_files = session_files[:limit]

    logger.info("Found %d OpenCode session files", len(session_files))

    if dry_run:
        for sf in session_files:
            oc = parse_opencode_session(sf)
            if oc is not None:
                result.ingested += 1
                result.session_ids.append(oc.session_id)
            else:
                result.errors += 1
                result.error_files.append(str(sf))
        return result

    # Initialize SDK
    try:
        sdk = SDK(agent=agent, directory=graph_dir)
    except Exception as e:
        logger.error("Failed to initialize HtmlGraph SDK: %s", e)
        result.errors += 1
        return result

    for session_file in session_files:
        oc = parse_opencode_session(session_file)
        if oc is None:
            result.errors += 1
            result.error_files.append(str(session_file))
            continue

        try:
            _ingest_single_session(sdk, oc)
            result.ingested += 1
            result.session_ids.append(oc.session_id)
            logger.debug("Ingested OpenCode session %s", oc.session_id)
        except Exception as e:
            logger.warning("Failed to ingest OpenCode session %s: %s", oc.session_id, e)
            result.errors += 1
            result.error_files.append(str(session_file))

    return result


def _ingest_single_session(sdk: Any, oc: OpenCodeSession) -> None:
    """Ingest a single OpenCodeSession into HtmlGraph via the SDK."""
    # Build a descriptive title
    title_parts: list[str] = ["opencode"]
    if oc.title:
        title_parts.append(oc.title[:80])
    title = ": ".join(title_parts)

    # Build handoff notes summarising the session
    models = oc.models_used
    notes_parts = [
        f"Source: {oc.source_file.name}",
        f"Project: {oc.project_id[:12]}",
        f"Directory: {oc.directory}",
        f"Messages: {len(oc.messages)} "
        f"(user={oc.user_turn_count}, assistant={oc.assistant_turn_count})",
    ]
    if oc.files_changed:
        notes_parts.append(
            f"Changes: +{oc.additions}/-{oc.deletions} in {oc.files_changed} files"
        )
    if models:
        notes_parts.append(f"Models: {', '.join(models[:5])}")
    notes = " | ".join(notes_parts)

    # Use a deterministic session ID derived from the OpenCode session ID
    htmlgraph_session_id = f"opencode-{oc.session_id}"

    session = sdk.session_manager.start_session(
        session_id=htmlgraph_session_id,
        agent=agent_name_from_sdk(sdk),
        title=title,
    )

    # Update session timing to match the original OpenCode session
    session.started_at = oc.created_at
    session.last_activity = oc.updated_at
    session.handoff_notes = notes

    # Mark as done since these are historical sessions
    session.status = "done"
    if not session.ended_at:
        session.ended_at = oc.updated_at

    sdk.session_manager.session_converter.save(session)


def agent_name_from_sdk(sdk: Any) -> str:
    """Extract agent name from SDK instance."""
    try:
        return sdk.agent  # type: ignore[no-any-return]
    except AttributeError:
        return "opencode"
