from __future__ import annotations

"""
SQLite analytics index for HtmlGraph event logs.

This is a rebuildable cache/index for fast dashboard queries.
The canonical source of truth is the JSONL event log under `.htmlgraph/events/`.
"""


import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 4  # Bumped: renamed 'agent' column to 'agent_assigned'


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
                try:
                    current_version = int(current["value"])
                except Exception:
                    current_version = None

                if current_version != SCHEMA_VERSION:
                    # The DB is a rebuildable cache (gitignored). When the schema changes,
                    # reset it in-place for a smoother UX.
                    conn.execute("DROP TABLE IF EXISTS event_files")
                    conn.execute("DROP TABLE IF EXISTS events")
                    conn.execute("DROP TABLE IF EXISTS sessions")
                    conn.execute("DROP TABLE IF EXISTS git_commits")
                    conn.execute("DROP TABLE IF EXISTS git_commit_parents")
                    conn.execute("DROP TABLE IF EXISTS git_commit_features")
                    conn.execute("DELETE FROM meta WHERE key='schema_version'")
                    conn.execute(
                        "INSERT INTO meta(key,value) VALUES('schema_version', ?)",
                        (str(SCHEMA_VERSION),),
                    )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_assigned TEXT,
                    start_commit TEXT,
                    continued_from TEXT,
                    status TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    parent_session_id TEXT,
                    parent_event_id TEXT
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
                    parent_event_id TEXT,
                    cost_tokens INTEGER,
                    execution_duration_seconds REAL,
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

            # Git commit graph tables (continuity spine)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_commits (
                    commit_hash TEXT PRIMARY KEY,
                    commit_hash_short TEXT,
                    ts TEXT,
                    branch TEXT,
                    author_name TEXT,
                    author_email TEXT,
                    subject TEXT,
                    message TEXT,
                    insertions INTEGER,
                    deletions INTEGER,
                    is_merge INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_commit_parents (
                    commit_hash TEXT NOT NULL,
                    parent_hash TEXT NOT NULL,
                    PRIMARY KEY(commit_hash, parent_hash),
                    FOREIGN KEY(commit_hash) REFERENCES git_commits(commit_hash)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS git_commit_features (
                    commit_hash TEXT NOT NULL,
                    feature_id TEXT NOT NULL,
                    PRIMARY KEY(commit_hash, feature_id),
                    FOREIGN KEY(commit_hash) REFERENCES git_commits(commit_hash)
                )
                """
            )

            # Indexes for typical dashboard queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_ts ON events(session_id, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_feature_ts ON events(feature_id, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_tool_ts ON events(tool, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_success_ts ON events(success, ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_files_path ON event_files(path)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_event_files_event_path ON event_files(event_id, path)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_git_commits_ts ON git_commits(ts)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_git_commit_features_feature ON git_commit_features(feature_id)"
            )

    def upsert_session(self, session: dict[str, Any]) -> None:
        """
        Upsert session metadata. Fields are best-effort; missing keys are allowed.
        """
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, agent_assigned, start_commit, continued_from, status, started_at, ended_at, parent_session_id, parent_event_id)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                    agent_assigned=excluded.agent_assigned,
                    start_commit=excluded.start_commit,
                    continued_from=excluded.continued_from,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    ended_at=excluded.ended_at,
                    parent_session_id=excluded.parent_session_id,
                    parent_event_id=excluded.parent_event_id
                """,
                (
                    session.get("session_id"),
                    session.get("agent"),
                    session.get("start_commit"),
                    session.get("continued_from"),
                    session.get("status"),
                    session.get("started_at"),
                    session.get("ended_at"),
                    session.get("parent_session_id"),
                    session.get("parent_event_id"),
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
            json.dumps(payload, ensure_ascii=False, default=str)
            if payload is not None
            else None
        )

        file_paths = event.get("file_paths") or []
        if not isinstance(file_paths, list):
            file_paths = []

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events(event_id, session_id, ts, tool, summary, success, feature_id, drift_score, payload_json, parent_event_id, cost_tokens, execution_duration_seconds)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
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
                    event.get("parent_event_id"),
                    event.get("cost_tokens"),
                    event.get("execution_duration_seconds"),
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
            conn.execute("DELETE FROM git_commit_features")
            conn.execute("DELETE FROM git_commit_parents")
            conn.execute("DELETE FROM git_commits")

            session_meta: dict[str, dict[str, Any]] = {}

            def normalize_event(event: dict[str, Any]) -> dict[str, Any] | None:
                """
                Normalize multiple on-disk event shapes into the AnalyticsIndex schema.

                Supported:
                - EventRecord JSON (event_id/tool/summary/...)
                - Legacy Git hook events ({type:"GitCommit", ...})
                """
                if event.get("event_id"):
                    return event

                legacy_type = event.get("type")
                if legacy_type in {"GitCommit", "GitCheckout", "GitMerge", "GitPush"}:
                    ts = event.get("timestamp") or event.get("ts")
                    session_id = event.get("session_id") or "git"
                    if not ts:
                        return None

                    features = (
                        event.get("features")
                        if isinstance(event.get("features"), list)
                        else []
                    )
                    feature_id = features[0] if features else None

                    # Best-effort deterministic IDs for GitCommit (by hash), otherwise timestamp-based.
                    if legacy_type == "GitCommit" and event.get("commit_hash"):
                        base = f"git-commit-{event.get('commit_hash')}"
                        event_id = (
                            base if feature_id is None else f"{base}-{feature_id}"
                        )
                        msg = (
                            (event.get("commit_message") or "").strip().splitlines()[0]
                            if event.get("commit_message")
                            else ""
                        )
                        summary = f"Commit {event.get('commit_hash_short', '')}: {msg}".strip()
                    else:
                        event_id = f"legacy-{legacy_type.lower()}-{ts}"
                        summary = legacy_type

                    file_paths = (
                        event.get("files_changed")
                        if isinstance(event.get("files_changed"), list)
                        else []
                    )

                    return {
                        "event_id": event_id,
                        "timestamp": ts,
                        "session_id": session_id,
                        "agent": event.get("agent") or "git",
                        "tool": legacy_type,
                        "summary": summary,
                        "success": True,
                        "feature_id": feature_id,
                        "drift_score": None,
                        "file_paths": file_paths,
                        "payload": event,
                    }

                return None

            for raw_event in events:
                event = normalize_event(raw_event)
                if event is None:
                    skipped += 1
                    continue

                event_id = event.get("event_id")
                session_id = event.get("session_id")
                ts = event.get("timestamp") or event.get("ts")
                if not event_id or not session_id or not ts:
                    skipped += 1
                    continue

                # Track session metadata from events (best-effort)
                meta = session_meta.setdefault(
                    session_id,
                    {
                        "session_id": session_id,
                        "agent": event.get("agent"),
                        "start_commit": event.get("start_commit"),
                        "continued_from": event.get("continued_from"),
                        "status": event.get("session_status"),
                        "started_at": None,
                        "ended_at": None,
                        "parent_session_id": event.get("parent_session_id"),
                        "parent_event_id": event.get("parent_event_id"),
                    },
                )
                if meta.get("agent") is None and event.get("agent"):
                    meta["agent"] = event.get("agent")
                if meta.get("start_commit") is None and event.get("start_commit"):
                    meta["start_commit"] = event.get("start_commit")
                if meta.get("continued_from") is None and event.get("continued_from"):
                    meta["continued_from"] = event.get("continued_from")
                if meta.get("status") is None and event.get("session_status"):
                    meta["status"] = event.get("session_status")
                if meta.get("parent_session_id") is None and event.get(
                    "parent_session_id"
                ):
                    meta["parent_session_id"] = event.get("parent_session_id")
                if meta.get("parent_event_id") is None and event.get("parent_event_id"):
                    meta["parent_event_id"] = event.get("parent_event_id")

                # Track time range (treat earliest event as started_at, latest as ended_at if session is ended)
                if meta["started_at"] is None or ts < meta["started_at"]:
                    meta["started_at"] = ts
                if meta["ended_at"] is None or ts > meta["ended_at"]:
                    meta["ended_at"] = ts

                payload = event.get("payload")
                payload_json = (
                    json.dumps(payload, ensure_ascii=False, default=str)
                    if payload is not None
                    else None
                )

                conn.execute(
                    """
                    INSERT OR IGNORE INTO events(event_id, session_id, ts, tool, summary, success, feature_id, drift_score, payload_json, parent_event_id, cost_tokens, execution_duration_seconds)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
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
                        event.get("parent_event_id"),
                        event.get("cost_tokens"),
                        event.get("execution_duration_seconds"),
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

                # Derive Git commit DAG rows from GitCommit events.
                if (event.get("tool") or "") == "GitCommit":
                    payload_dict: dict[str, Any] | None = None
                    if isinstance(event.get("payload"), dict):
                        payload_dict = event.get("payload")
                    else:
                        try:
                            if payload_json:
                                payload_dict = json.loads(payload_json)
                        except Exception:
                            payload_dict = None

                    if payload_dict and payload_dict.get("type") == "GitCommit":
                        commit_hash = payload_dict.get("commit_hash")
                        if commit_hash:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO git_commits(
                                    commit_hash, commit_hash_short, ts, branch, author_name, author_email,
                                    subject, message, insertions, deletions, is_merge
                                )
                                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    str(commit_hash),
                                    payload_dict.get("commit_hash_short"),
                                    ts,
                                    payload_dict.get("branch"),
                                    payload_dict.get("author_name"),
                                    payload_dict.get("author_email"),
                                    payload_dict.get("subject"),
                                    payload_dict.get("commit_message"),
                                    payload_dict.get("insertions"),
                                    payload_dict.get("deletions"),
                                    1 if payload_dict.get("is_merge") else 0,
                                ),
                            )

                            parents = payload_dict.get("parents") or []
                            if isinstance(parents, list):
                                for parent in parents:
                                    if not parent:
                                        continue
                                    conn.execute(
                                        "INSERT OR IGNORE INTO git_commit_parents(commit_hash, parent_hash) VALUES(?,?)",
                                        (str(commit_hash), str(parent)),
                                    )

                            features = payload_dict.get("features") or []
                            if isinstance(features, list):
                                for fid in features:
                                    if not fid:
                                        continue
                                    conn.execute(
                                        "INSERT OR IGNORE INTO git_commit_features(commit_hash, feature_id) VALUES(?,?)",
                                        (str(commit_hash), str(fid)),
                                    )

                inserted += 1

            # Upsert sessions after loading all events.
            for meta in session_meta.values():
                conn.execute(
                    """
                    INSERT INTO sessions(session_id, agent_assigned, start_commit, continued_from, status, started_at, ended_at, parent_session_id, parent_event_id)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        meta.get("session_id"),
                        meta.get("agent"),  # Source data still uses 'agent' key
                        meta.get("start_commit"),
                        meta.get("continued_from"),
                        meta.get("status"),
                        meta.get("started_at"),
                        meta.get("ended_at"),
                        meta.get("parent_session_id"),
                        meta.get("parent_event_id"),
                    ),
                )

        return {"inserted": inserted, "skipped": skipped}

    # ---------------------------------------------------------------------
    # Git continuity queries
    # ---------------------------------------------------------------------

    def feature_commits(
        self, feature_id: str, limit: int = 200
    ) -> list[dict[str, Any]]:
        """
        Return commit timeline for a feature based on GitCommit events.
        """
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.commit_hash, c.commit_hash_short, c.ts, c.branch, c.author_name, c.author_email,
                       c.subject, c.insertions, c.deletions, c.is_merge
                FROM git_commit_features f
                JOIN git_commits c ON c.commit_hash = f.commit_hash
                WHERE f.feature_id = ?
                ORDER BY c.ts DESC
                LIMIT ?
                """,
                (feature_id, int(limit)),
            ).fetchall()

            parents = conn.execute(
                """
                SELECT commit_hash, COUNT(*) AS parent_count
                FROM git_commit_parents
                WHERE commit_hash IN (SELECT commit_hash FROM git_commit_features WHERE feature_id = ?)
                GROUP BY commit_hash
                """,
                (feature_id,),
            ).fetchall()

        parent_counts = {r["commit_hash"]: int(r["parent_count"] or 0) for r in parents}
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["parent_count"] = parent_counts.get(d["commit_hash"], 0)
            out.append(d)
        return out

    def feature_commit_graph(self, feature_id: str, limit: int = 200) -> dict[str, Any]:
        """
        Return a minimal DAG representation (nodes + edges) for a feature's commits.
        """
        commits = self.feature_commits(feature_id=feature_id, limit=limit)
        commit_hashes = {c["commit_hash"] for c in commits if c.get("commit_hash")}
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT commit_hash, parent_hash
                FROM git_commit_parents
                WHERE commit_hash IN (
                    SELECT commit_hash FROM git_commit_features WHERE feature_id = ?
                )
                """,
                (feature_id,),
            ).fetchall()

        edges: list[dict[str, Any]] = []
        external: set[str] = set()
        for r in rows:
            parent = r["parent_hash"]
            if parent and parent not in commit_hashes:
                external.add(parent)
            edges.append({"from": parent, "to": r["commit_hash"]})

        nodes = [
            {
                "id": c["commit_hash"],
                **{
                    k: c.get(k)
                    for k in (
                        "commit_hash_short",
                        "ts",
                        "branch",
                        "subject",
                        "is_merge",
                        "insertions",
                        "deletions",
                    )
                },
            }
            for c in commits
        ]
        for parent in sorted(external):
            nodes.append(
                {"id": parent, "commit_hash_short": parent[:7], "external": True}
            )

        return {"nodes": nodes, "edges": edges}

    # ---------------------------------------------------------------------
    # Query helpers for API
    # ---------------------------------------------------------------------

    def overview(
        self, since: str | None = None, until: str | None = None
    ) -> dict[str, Any]:
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
            "failure_rate": (float(row["failures"] or 0) / float(row["events"] or 1)),
            "avg_drift": row["avg_drift"],
            "top_tools": [dict(r) for r in by_tool],
        }

    def top_features(
        self, since: str | None = None, until: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
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
                SELECT e.event_id, e.session_id, e.ts, e.tool, e.summary, e.success, e.feature_id, e.drift_score,
                       COALESCE(e.parent_event_id, s.parent_event_id) as parent_event_id,
                       e.cost_tokens, e.execution_duration_seconds
                FROM events e
                JOIN sessions s ON e.session_id = s.session_id
                WHERE e.session_id = ?
                   OR s.parent_session_id = ?
                ORDER BY e.ts DESC
                LIMIT ?
                """,
                (session_id, session_id, int(limit)),
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


def _time_where_clause(
    column: str, since: str | None, until: str | None
) -> tuple[str, tuple[Any, ...]]:
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
