from __future__ import annotations

"""Cursor AI Session Ingester.

Reads Cursor's AI tracking database from ~/.cursor/ai-tracking/ai-code-tracking.db
and project conversation data, then creates HtmlGraph session records.

Cursor stores AI interaction data in a SQLite database:
    ~/.cursor/ai-tracking/ai-code-tracking.db

Relevant tables:
    - conversation_summaries: Summarised conversations with metadata
        conversationId TEXT PK
        title TEXT
        tldr TEXT
        overview TEXT
        summaryBullets TEXT (JSON array)
        model TEXT
        mode TEXT
        updatedAt INTEGER (unix-ms)

Cursor also maintains a projects directory:
    ~/.cursor/projects/<encoded-project-path>/
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default Cursor AI tracking database location
_CURSOR_DEFAULT_DB_PATH = (
    Path.home() / ".cursor" / "ai-tracking" / "ai-code-tracking.db"
)

# Default Cursor projects directory
_CURSOR_PROJECTS_DIR = Path.home() / ".cursor" / "projects"


@dataclass
class CursorConversation:
    """A single Cursor AI conversation summary."""

    conversation_id: str
    title: str | None
    tldr: str | None
    overview: str | None
    summary_bullets: list[str]
    model: str | None
    mode: str | None
    updated_at: datetime

    @classmethod
    def from_row(cls, row: tuple[Any, ...], columns: list[str]) -> CursorConversation:
        """Parse a database row into a CursorConversation."""
        data = dict(zip(columns, row))

        updated_ms = data.get("updatedAt", 0) or 0
        try:
            updated_at = datetime.fromtimestamp(updated_ms / 1000.0, tz=timezone.utc)
        except (ValueError, OSError):
            updated_at = datetime.now(tz=timezone.utc)

        # Parse summaryBullets JSON
        bullets_raw = data.get("summaryBullets") or "[]"
        try:
            bullets: list[str] = json.loads(bullets_raw)
            if not isinstance(bullets, list):
                bullets = []
        except (json.JSONDecodeError, TypeError):
            bullets = []

        return cls(
            conversation_id=data.get("conversationId", ""),
            title=data.get("title") or None,
            tldr=data.get("tldr") or None,
            overview=data.get("overview") or None,
            summary_bullets=bullets,
            model=data.get("model") or None,
            mode=data.get("mode") or None,
            updated_at=updated_at,
        )

    @property
    def description(self) -> str:
        """Return a human-readable description of this conversation."""
        if self.title:
            return self.title
        if self.tldr:
            return self.tldr[:120]
        if self.summary_bullets:
            return self.summary_bullets[0][:120]
        return f"Cursor conversation {self.conversation_id[:12]}"


def find_cursor_db(db_path: Path | None = None) -> Path | None:
    """Find the Cursor AI tracking database.

    Args:
        db_path: Explicit path to the database file. If None, checks default location.

    Returns:
        Path to the database file, or None if not found.
    """
    if db_path is not None:
        p = Path(db_path)
        return p if p.exists() else None

    if _CURSOR_DEFAULT_DB_PATH.exists():
        return _CURSOR_DEFAULT_DB_PATH

    return None


def load_cursor_conversations(
    db_path: Path | None = None,
    limit: int | None = None,
) -> list[CursorConversation]:
    """Load Cursor conversation summaries from the tracking database.

    Args:
        db_path: Path to the Cursor tracking database. If None, checks default location.
        limit: Maximum number of conversations to load (newest first).

    Returns:
        List of CursorConversation objects sorted by updatedAt (newest first).
        Returns empty list if database not found or query fails.
    """
    resolved_db = find_cursor_db(db_path)
    if resolved_db is None:
        logger.debug("Cursor tracking database not found")
        return []

    try:
        conn = sqlite3.connect(str(resolved_db))
        try:
            cursor = conn.cursor()

            # Check table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_summaries'"
            )
            if not cursor.fetchone():
                logger.debug("conversation_summaries table not found in Cursor DB")
                return []

            query = "SELECT * FROM conversation_summaries ORDER BY updatedAt DESC"
            if limit is not None:
                query += f" LIMIT {int(limit)}"

            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return [CursorConversation.from_row(row, columns) for row in rows]

        finally:
            conn.close()

    except sqlite3.Error as e:
        logger.warning("Failed to query Cursor database %s: %s", resolved_db, e)
        return []


@dataclass
class IngestResult:
    """Result of ingesting Cursor sessions into HtmlGraph."""

    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    session_ids: list[str] = field(default_factory=list)
    error_files: list[str] = field(default_factory=list)


def ingest_cursor_sessions(
    graph_dir: str | Path | None = None,
    agent: str = "cursor",
    db_path: Path | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest Cursor AI conversations into HtmlGraph.

    Reads from Cursor's AI tracking SQLite database, parses conversation
    summaries, and creates corresponding HtmlGraph session records.
    Sessions are identified by their Cursor conversation ID and are
    idempotent - re-ingesting the same conversation will update it.

    Args:
        graph_dir: Path to .htmlgraph directory. Auto-discovered if None.
        agent: Agent name to attribute sessions to (default: "cursor").
        db_path: Override for Cursor tracking database path. If None, uses default.
        limit: Maximum number of conversations to ingest. If None, ingest all.
        dry_run: If True, parse and report but do not write to HtmlGraph.

    Returns:
        IngestResult with counts of ingested, skipped, and errored conversations.
    """
    from htmlgraph import SDK

    result = IngestResult()

    # Load conversations from database
    conversations = load_cursor_conversations(db_path=db_path, limit=limit)
    if not conversations:
        logger.info("No Cursor conversations found")
        return result

    logger.info("Found %d Cursor conversations", len(conversations))

    if dry_run:
        for conv in conversations:
            if conv.conversation_id:
                result.ingested += 1
                result.session_ids.append(conv.conversation_id)
            else:
                result.errors += 1
                result.error_files.append(f"conversation-{result.errors}")
        return result

    # Initialize SDK
    try:
        sdk = SDK(agent=agent, directory=graph_dir)
    except Exception as e:
        logger.error("Failed to initialize HtmlGraph SDK: %s", e)
        result.errors += 1
        return result

    for conv in conversations:
        if not conv.conversation_id:
            result.errors += 1
            result.error_files.append("(missing conversation ID)")
            continue

        try:
            _ingest_single_conversation(sdk, conv, agent)
            result.ingested += 1
            result.session_ids.append(conv.conversation_id)
            logger.debug("Ingested Cursor conversation %s", conv.conversation_id)
        except Exception as e:
            logger.warning(
                "Failed to ingest Cursor conversation %s: %s", conv.conversation_id, e
            )
            result.errors += 1
            result.error_files.append(conv.conversation_id)

    return result


def _ingest_single_conversation(
    sdk: Any, conv: CursorConversation, agent: str = "cursor"
) -> None:
    """Ingest a single CursorConversation into HtmlGraph via the SDK."""
    # Build title
    title_parts: list[str] = ["cursor"]
    desc = conv.description
    if desc:
        title_parts.append(desc[:80])
    title = ": ".join(title_parts)

    # Build handoff notes
    notes_parts: list[str] = []
    if conv.tldr:
        notes_parts.append(f"Summary: {conv.tldr[:200]}")
    if conv.model:
        notes_parts.append(f"Model: {conv.model}")
    if conv.mode:
        notes_parts.append(f"Mode: {conv.mode}")
    if conv.summary_bullets:
        notes_parts.append(f"Key points: {'; '.join(conv.summary_bullets[:3])}")
    notes = " | ".join(notes_parts) if notes_parts else "Cursor conversation"

    # Deterministic session ID from conversation ID
    safe_id = conv.conversation_id.replace("/", "-").replace("\\", "-")[:40]
    htmlgraph_session_id = f"cursor-{safe_id}"

    session = sdk.session_manager.start_session(
        session_id=htmlgraph_session_id,
        agent=agent,
        title=title,
    )

    # Set timing from Cursor's updatedAt
    session.started_at = conv.updated_at
    session.last_activity = conv.updated_at
    session.handoff_notes = notes

    # Mark as done since these are historical sessions
    session.status = "done"
    if not session.ended_at:
        session.ended_at = conv.updated_at

    sdk.session_manager.session_converter.save(session)
