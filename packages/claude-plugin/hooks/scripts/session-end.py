#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
HtmlGraph Session End Hook

Records session end and generates summary.
Uses htmlgraph Python API directly for all storage operations.
"""

import json
import os
import sys

# Bootstrap Python path and setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bootstrap import bootstrap_pythonpath, is_tracking_disabled, resolve_project_dir

if is_tracking_disabled():
    print(json.dumps({}))
    sys.exit(0)

project_dir_for_import = resolve_project_dir()
bootstrap_pythonpath(project_dir_for_import)

from pathlib import Path

try:
    from htmlgraph.session_manager import SessionManager
except Exception as e:
    print(
        f"Warning: HtmlGraph not available ({e}). Install with: pip install htmlgraph",
        file=sys.stderr,
    )
    print(json.dumps({}))
    sys.exit(0)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    external_session_id = hook_input.get("session_id") or os.environ.get(
        "CLAUDE_SESSION_ID"
    )
    cwd = hook_input.get("cwd")
    project_dir = resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Session lifecycle management
    # Note: Transcript import happens on work item completion or git commit,
    # not on session end (sessions can end frequently during context switches)
    try:
        manager = SessionManager(graph_dir)
        active = manager.get_active_session()

        # Link transcript to session (but don't import events yet)
        if active and external_session_id:
            try:
                from htmlgraph.transcript import TranscriptReader

                reader = TranscriptReader()
                transcript = reader.read_session(external_session_id)
                if transcript:
                    # Just link, don't import - import happens on commit/completion
                    manager.link_transcript(
                        session_id=active.id,
                        transcript_id=external_session_id,
                        transcript_path=str(transcript.path),
                        git_branch=transcript.git_branch,
                    )
            except Exception:
                pass

        # Optional handoff context capture (non-interactive)
        handoff_notes = hook_input.get("handoff_notes") or os.environ.get(
            "HTMLGRAPH_HANDOFF_NOTES"
        )
        recommended_next = hook_input.get("recommended_next") or os.environ.get(
            "HTMLGRAPH_HANDOFF_RECOMMEND"
        )
        blockers_raw = hook_input.get("blockers") or os.environ.get(
            "HTMLGRAPH_HANDOFF_BLOCKERS"
        )
        blockers = None
        if isinstance(blockers_raw, str):
            blockers = [b.strip() for b in blockers_raw.split(",") if b.strip()]
        elif isinstance(blockers_raw, list):
            blockers = [str(b).strip() for b in blockers_raw if str(b).strip()]

        if active and (handoff_notes or recommended_next or blockers):
            try:
                manager.set_session_handoff(
                    session_id=active.id,
                    handoff_notes=handoff_notes,
                    recommended_next=recommended_next,
                    blockers=blockers,
                )
            except Exception:
                pass
        elif sys.stderr.isatty():
            print(
                "HtmlGraph: add handoff notes with 'uv run htmlgraph session handoff --notes ...'",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"Warning: Could not end session: {e}", file=sys.stderr)

    # Output empty response (session end doesn't add context)
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
