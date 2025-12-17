"""
SQLite analytics index for HtmlGraph event logs.

This is a rebuildable cache/index for fast dashboard queries.
The canonical source of truth is the JSONL event log under `.htmlgraph/events/`.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class IndexPaths:
    graph_dir: Path

    @property
    def db_path(self) -> Path:
        return self.graph_dir / "index.sqlite"

    @property
    def events_dir(self) -> Path:
        return self.graph_dir / "events"


class AnalyticsIndex:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA busy_timeout=3000;")
        return conn

    def ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            current = conn.execute(
                "SELECT value FROM meta WHERE key='schema_version'"
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO meta(key,value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            else:
                # For now we only support a single schema version.
                if int(current["value"]) != SCHEMA_VERSION:
                    raise RuntimeError(
                        f"Unsupported analytics index schema: {current['value']}"
                    )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent TEXT,
                    start_commit TEXT,
                    continued_from TEXT,
                    status TEXT,
                    started_at TEXT,
                    ended_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    feature_id TEXT,
                    drift_score REAL,
                    payload_json TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_files (
                    event_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(event_id)
                )
                """
            )

            # Indexes for typical dashboard queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_ts ON events(session_id, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_feature_ts ON events(feature_id, ts)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_tool_ts ON events(tool, ts)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_success_ts ON events(success, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_files_path ON event_files(path)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_event_files_event_path ON event_files(event_id, path)"
            )

    def upsert_session(self, session: dict[str, Any]) -> None:
        """
        Upsert session metadata. Fields are best-effort; missing keys are allowed.
        """
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, agent, start_commit, continued_from, status, started_at, ended_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                    agent=excluded.agent,
                    start_commit=excluded.start_commit,
                    continued_from=excluded.continued_from,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    ended_at=excluded.ended_at
                """,
                (
                    session.get("session_id"),
                    session.get("agent"),
                    session.get("start_commit"),
                    session.get("continued_from"),
                    session.get("status"),
                    session.get("started_at"),
                    session.get("ended_at"),
                ),
            )

    def upsert_event(self, event: dict[str, Any]) -> None:
        """
        Insert an event if not present (idempotent).
        """
        event_id = event.get("event_id")
        if not event_id:
            return

        session_id = event.get("session_id")
        ts = event.get("timestamp") or event.get("ts")
        if not session_id or not ts:
            return

        payload = event.get("payload")
        payload_json = (
            json.dumps(payload, ensure_ascii=False, default=str) if payload is not None else None
        )

        file_paths = event.get("file_paths") or []
        if not isinstance(file_paths, list):
            file_paths = []

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events(event_id, session_id, ts, tool, summary, success, feature_id, drift_score, payload_json)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    event_id,
                    session_id,
                    ts,
                    event.get("tool") or "unknown",
                    event.get("summary") or "",
                    1 if event.get("success", True) else 0,
                    event.get("feature_id"),
                    event.get("drift_score"),
                    payload_json,
                ),
            )
            # Insert file path rows, idempotent by (event_id, path)
            for p in file_paths:
                if not p:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO event_files(event_id, path) VALUES(?, ?)",
                    (event_id, str(p)),
                )

    def rebuild_from_events(self, events: Iterable[dict[str, Any]]) -> dict[str, int]:
        """
        Rebuild the index from a stream of event dicts.
        """
        self.ensure_schema()
        inserted = 0
        skipped = 0

        with self.connect() as conn:
            conn.execute("DELETE FROM event_files")
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM sessions")

            session_meta: dict[str, dict[str, Any]] = {}

            for event in events:
                event_id = event.get("event_id")
                session_id = event.get("session_id")
                ts = event.get("timestamp") or event.get("ts")
                if not event_id or not session_id or not ts:
                    skipped += 1
                    continue

                # Track session metadata from events (best-effort)
                meta = session_meta.setdefault(session_id, {
                    "session_id": session_id,
                    "agent": event.get("agent"),
                    "start_commit": event.get("start_commit"),
                    "continued_from": event.get("continued_from"),
                    "status": event.get("session_status"),
                    "started_at": None,
                    "ended_at": None,
                })
                if meta.get("agent") is None and event.get("agent"):
                    meta["agent"] = event.get("agent")
                if meta.get("start_commit") is None and event.get("start_commit"):
                    meta["start_commit"] = event.get("start_commit")
                if meta.get("continued_from") is None and event.get("continued_from"):
                    meta["continued_from"] = event.get("continued_from")
                if meta.get("status") is None and event.get("session_status"):
                    meta["status"] = event.get("session_status")

                # Track time range (treat earliest event as started_at, latest as ended_at if session is ended)
                if meta["started_at"] is None or ts < meta["started_at"]:
                    meta["started_at"] = ts
                if meta["ended_at"] is None or ts > meta["ended_at"]:
                    meta["ended_at"] = ts

                payload = event.get("payload")
                payload_json = (
                    json.dumps(payload, ensure_ascii=False, default=str) if payload is not None else None
                )

                conn.execute(
                    """
                    INSERT OR IGNORE INTO events(event_id, session_id, ts, tool, summary, success, feature_id, drift_score, payload_json)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_id,
                        session_id,
                        ts,
                        event.get("tool") or "unknown",
                        event.get("summary") or "",
                        1 if event.get("success", True) else 0,
                        event.get("feature_id"),
                        event.get("drift_score"),
                        payload_json,
                    ),
                )

                file_paths = event.get("file_paths") or []
                if isinstance(file_paths, list):
                    for p in file_paths:
                        if not p:
                            continue
                        conn.execute(
                            "INSERT OR IGNORE INTO event_files(event_id, path) VALUES(?, ?)",
                            (event_id, str(p)),
                        )

                inserted += 1

            # Upsert sessions after loading all events.
            for meta in session_meta.values():
                conn.execute(
                    """
                    INSERT INTO sessions(session_id, agent, start_commit, continued_from, status, started_at, ended_at)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        meta.get("session_id"),
                        meta.get("agent"),
                        meta.get("start_commit"),
                        meta.get("continued_from"),
                        meta.get("status"),
                        meta.get("started_at"),
                        meta.get("ended_at"),
                    ),
                )

        return {"inserted": inserted, "skipped": skipped}

    # ---------------------------------------------------------------------
    # Query helpers for API
    # ---------------------------------------------------------------------

    def overview(self, since: str | None = None, until: str | None = None) -> dict[str, Any]:
        """
        Return overview stats.
        since/until should be ISO8601 timestamps.
        """
        self.ensure_schema()
        where, params = _time_where_clause("ts", since, until)
        with self.connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                  COUNT(*) AS events,
                  SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS failures,
                  AVG(CASE WHEN drift_score IS NULL THEN NULL ELSE drift_score END) AS avg_drift
                FROM events
                {where}
                """,
                params,
            ).fetchone()
            by_tool = conn.execute(
                f"""
                SELECT tool, COUNT(*) AS count,
                       SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS failures
                FROM events
                {where}
                GROUP BY tool
                ORDER BY count DESC
                LIMIT 20
                """,
                params,
            ).fetchall()

        return {
            "events": int(row["events"] or 0),
            "failures": int(row["failures"] or 0),
            "failure_rate": (
                float(row["failures"] or 0) / float(row["events"] or 1)
            ),
            "avg_drift": row["avg_drift"],
            "top_tools": [dict(r) for r in by_tool],
        }

    def top_features(self, since: str | None = None, until: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        self.ensure_schema()
        clauses = []
        params: list[Any] = []
        if since:
            clauses.append("ts >= ?")
            params.append(since)
        if until:
            clauses.append("ts <= ?")
            params.append(until)
        clauses.append("feature_id IS NOT NULL")
        clauses.append("feature_id != ''")
        where = "WHERE " + " AND ".join(clauses)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT feature_id, COUNT(*) AS count,
                       SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS failures,
                       AVG(CASE WHEN drift_score IS NULL THEN NULL ELSE drift_score END) AS avg_drift
                FROM events
                {where}
                GROUP BY feature_id
                ORDER BY count DESC
                LIMIT ?
                """,
                (*params, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def session_events(self, session_id: str, limit: int = 500) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, session_id, ts, tool, summary, success, feature_id, drift_score
                FROM events
                WHERE session_id=?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (session_id, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def feature_continuity(
        self,
        feature_id: str,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """
        Return sessions that touched a feature, ordered by first activity timestamp.
        """
        self.ensure_schema()
        where, params = _time_where_clause("e.ts", since, until)
        if where:
            where += " AND e.feature_id = ?"
        else:
            where = "WHERE e.feature_id = ?"
        params = (*params, feature_id)

        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                  e.session_id,
                  s.agent,
                  s.start_commit,
                  s.continued_from,
                  s.status,
                  MIN(e.ts) AS first_ts,
                  MAX(e.ts) AS last_ts,
                  COUNT(*) AS events,
                  SUM(CASE WHEN e.success=0 THEN 1 ELSE 0 END) AS failures,
                  AVG(CASE WHEN e.drift_score IS NULL THEN NULL ELSE e.drift_score END) AS avg_drift
                FROM events e
                LEFT JOIN sessions s ON s.session_id = e.session_id
                {where}
                GROUP BY e.session_id
                ORDER BY first_ts ASC
                LIMIT ?
                """,
                (*params, int(limit)),
            ).fetchall()

        return [dict(r) for r in rows]

    def top_tool_transitions(
        self,
        since: str | None = None,
        until: str | None = None,
        feature_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return the most common tool -> next_tool transitions (bigrams) per session timeline.
        """
        self.ensure_schema()
        where, params = _time_where_clause("ts", since, until)
        clauses = []
        if where:
            clauses.append(where.replace("WHERE ", "", 1))
        if feature_id:
            clauses.append("feature_id = ?")
            params = (*params, feature_id)
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        with self.connect() as conn:
            rows = conn.execute(
                f"""
                WITH ordered AS (
                  SELECT
                    session_id,
                    ts,
                    tool,
                    LEAD(tool) OVER (PARTITION BY session_id ORDER BY ts) AS next_tool
                  FROM events
                  {where_sql}
                )
                SELECT tool, next_tool, COUNT(*) AS count
                FROM ordered
                WHERE next_tool IS NOT NULL AND next_tool != ''
                GROUP BY tool, next_tool
                ORDER BY count DESC
                LIMIT ?
                """,
                (*params, int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]


def _time_where_clause(column: str, since: str | None, until: str | None) -> tuple[str, tuple[Any, ...]]:
    clauses = []
    params: list[Any] = []
    if since:
        clauses.append(f"{column} >= ?")
        params.append(since)
    if until:
        clauses.append(f"{column} <= ?")
        params.append(until)
    if not clauses:
        return "", tuple()
    return "WHERE " + " AND ".join(clauses), tuple(params)
