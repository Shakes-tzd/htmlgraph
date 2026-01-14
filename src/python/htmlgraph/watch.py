from __future__ import annotations

"""
File-change watcher for HtmlGraph.

This is a pragmatic way to track agent activity when your tooling doesn't provide
native "PostToolUse" hooks (e.g. editors/agents that write files directly).

It batches filesystem changes and records them as activity events.
"""


import os
import time
from dataclasses import dataclass
from pathlib import Path

from htmlgraph.session_manager import SessionManager

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    ".htmlgraph",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".playwright-mcp",
}


@dataclass
class FileSnapshot:
    mtime: float
    size: int


def _iter_files(root: Path, ignore_dirs: set[str]) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for name in filenames:
            files.append(Path(dirpath) / name)
    return files


def _snapshot(root: Path, ignore_dirs: set[str]) -> dict[str, FileSnapshot]:
    snap: dict[str, FileSnapshot] = {}
    for path in _iter_files(root, ignore_dirs):
        try:
            st = path.stat()
        except OSError:
            continue
        rel = str(path.relative_to(root))
        snap[rel] = FileSnapshot(mtime=st.st_mtime, size=st.st_size)
    return snap


def watch_and_track(
    root: Path,
    graph_dir: Path,
    session_id: str | None,
    agent: str,
    interval_seconds: float = 2.0,
    batch_seconds: float = 5.0,
    ignore_dirs: set[str] | None = None,
) -> None:
    ignore = set(ignore_dirs or DEFAULT_IGNORE_DIRS)

    manager = SessionManager(graph_dir)
    session = manager.start_session(
        session_id=session_id, agent=agent, title=f"Watch: {agent}"
    )

    last_snapshot = _snapshot(root, ignore)
    pending: set[str] = set()
    last_flush = time.time()

    print(f"Watching {root} (interval={interval_seconds}s, batch={batch_seconds}s)")
    print(f"Logging to session: {session.id}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(interval_seconds)
            current = _snapshot(root, ignore)

            changed: set[str] = set()
            # Detect modified/created files
            for rel, meta in current.items():
                prev = last_snapshot.get(rel)
                if prev is None:
                    changed.add(rel)
                elif meta.mtime != prev.mtime or meta.size != prev.size:
                    changed.add(rel)

            # Detect deletions
            for rel in last_snapshot.keys():
                if rel not in current:
                    changed.add(rel)

            if changed:
                pending.update(sorted(changed))

            now = time.time()
            should_flush = pending and (now - last_flush >= batch_seconds)
            if should_flush:
                paths = sorted(pending)[:50]
                more = len(pending) - len(paths)
                suffix = f" (+{more} more)" if more > 0 else ""
                summary = f"File changes: {len(pending)}{suffix}"

                manager.track_activity(
                    session_id=session.id,
                    tool="FSWatch",
                    summary=summary,
                    file_paths=paths,
                    payload={"root": str(root), "count": len(pending), "more": more},
                )
                pending.clear()
                last_flush = now
                print(summary)

            last_snapshot = current
    except KeyboardInterrupt:
        print("\nStopping watcher…")
        manager.track_activity(
            session_id=session.id, tool="Stop", summary="Watcher stopped"
        )
        manager.end_session(session.id)
