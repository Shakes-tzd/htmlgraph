from __future__ import annotations

"""
Helpers to migrate legacy session HTML activity logs to JSONL event logs.
"""


import json
from pathlib import Path
from typing import Any

from htmlgraph.converter import html_to_session


def export_sessions_to_jsonl(
    sessions_dir: Path | str,
    events_dir: Path | str,
    overwrite: bool = False,
    include_subdirs: bool = False,
) -> dict[str, int]:
    sessions_dir = Path(sessions_dir)
    events_dir = Path(events_dir)
    events_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    failed = 0

    pattern = "**/*.html" if include_subdirs else "*.html"
    for path in sessions_dir.glob(pattern):
        if path.is_dir():
            continue
        try:
            session = html_to_session(path)
        except Exception:
            failed += 1
            continue

        out_path = events_dir / f"{session.id}.jsonl"
        if out_path.exists() and not overwrite:
            skipped += 1
            continue

        # Serialize as one JSON object per line, oldest -> newest.
        lines: list[str] = []
        for entry in session.activity_log:
            payload: dict[str, Any] | None = (
                entry.payload if isinstance(entry.payload, dict) else None
            )
            file_paths = None
            if (
                payload
                and "file_paths" in payload
                and isinstance(payload["file_paths"], list)
            ):
                file_paths = payload["file_paths"]

            event = {
                "event_id": entry.id or f"{session.id}-{len(lines)}",
                "timestamp": entry.timestamp.isoformat(),
                "session_id": session.id,
                "agent": session.agent,
                "tool": entry.tool,
                "summary": entry.summary,
                "success": entry.success,
                "feature_id": entry.feature_id,
                "drift_score": entry.drift_score,
                "start_commit": session.start_commit,
                "continued_from": session.continued_from,
                "session_status": session.status,
                "file_paths": file_paths or [],
                "payload": payload,
            }
            lines.append(json.dumps(event, ensure_ascii=False, default=str))

        out_path.write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
        )
        written += 1

    return {"written": written, "skipped": skipped, "failed": failed}
