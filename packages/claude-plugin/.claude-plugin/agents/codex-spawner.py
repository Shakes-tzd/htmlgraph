#!/usr/bin/env python3
"""
Codex Spawner Agent - Executable wrapper for Codex CLI with event tracking.

ARCHITECTURE:
  This spawner agent is invoked by the HtmlGraph orchestrator via Task() delegation.
  It acts as a transparent wrapper around the Codex CLI, providing:

  1. Argument parsing for Codex-specific options (sandbox, models, etc.)
  2. Environment context propagation (parent session, event tracking)
  3. Event tracking in HtmlGraph database
  4. Transparent error handling with JSON responses
  5. Result aggregation and reporting

ERROR HANDLING:
  All errors are returned as JSON to stderr with "success": false.
  The orchestrator interprets error types:

  - CLI not found: Suggests installation (npm install -g @openai/codex-cli)
  - Authentication failed: Prompts for OpenAI API key setup
  - Sandbox restriction: Provides fallback modes or retries
  - Timeout: Increases timeout or breaks task into smaller chunks
  - Network/API error: Retries with backoff

  This transparent error format allows orchestrator to implement smart
  fallback strategies without parsing stdout/stderr text.

BASH INVOCATION (for orchestrator):
  Standard Task() delegation handles invocation:

    Task(
        subagent_type="codex",
        prompt="Implement REST API for user management",
        sandbox="workspace-write",
        timeout=180
    )

  The spawner-router hook converts this to:

    /path/to/codex-spawner.py \
      -p "Implement REST API for user management" \
      --sandbox workspace-write \
      --timeout 180

  Environment variables are set by router before spawning:

    HTMLGRAPH_PARENT_SESSION=session-xyz
    HTMLGRAPH_PARENT_EVENT=event-abc
    HTMLGRAPH_PARENT_QUERY_EVENT=query-123
    HTMLGRAPH_PARENT_AGENT=orchestrator

SANDBOX MODES:
  - read-only: Can read files but not modify
  - workspace-write: Can modify files in workspace
  - full: All operations (use with caution)
"""

import argparse
import json
import os
import sys
import time
import uuid
from typing import Any


def _parse_codex_events(
    output: str,
    tracker: Any,
    phase_event_id: str,
) -> None:
    """
    Parse Codex CLI JSON output and record tool calls as child events.

    The Codex CLI with --output-json produces JSON output with tool events:
    {"type": "tool_use", "tool": "bash", "input": {"command": "..."}}
    {"type": "tool_result", "tool": "bash", "output": "...", "success": true}

    Args:
        output: JSON/JSONL output from Codex CLI
        tracker: SpawnerEventTracker instance
        phase_event_id: Parent execution phase event ID
    """
    tool_call_ids: dict[
        str, str
    ] = {}  # Maps tool_name -> event_id for matching results

    for line in output.strip().splitlines():
        if not line.strip():
            continue

        try:
            event = json.loads(line)
            event_type = event.get("type")

            if event_type == "tool_use":
                tool_name = event.get("tool", "unknown")
                tool_input = event.get("input", {})

                # Record the tool call
                result = tracker.record_tool_call(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    phase_event_id=phase_event_id,
                    spawned_agent="gpt-4",
                )

                if result:
                    tool_call_ids[tool_name] = result.get("event_id")

            elif event_type == "tool_result":
                tool_name = event.get("tool", "unknown")

                # Complete the tool call if we have a matching record
                if tool_name in tool_call_ids:
                    tool_output = event.get("output", "")
                    success = event.get("success", True)

                    tracker.complete_tool_call(
                        event_id=tool_call_ids[tool_name],
                        output_summary=str(tool_output)[:500],
                        success=success,
                    )

        except json.JSONDecodeError:
            # Skip non-JSON lines (e.g., raw output)
            continue
        except Exception:
            # Non-fatal - continue processing remaining events
            continue


def main() -> None:
    """Execute Codex spawner with comprehensive event tracking and delegation records."""
    parser = argparse.ArgumentParser(
        description="Spawn Codex AI agent in headless mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p "Implement a feature" --sandbox workspace-write
  %(prog)s -p "Fix bugs in project" -m gpt-4-turbo
  %(prog)s -p "Generate documentation" --sandbox read-only
        """,
    )

    parser.add_argument(
        "-p",
        "--prompt",
        required=True,
        help="Task description for Codex",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Model selection (e.g., 'gpt-4-turbo'). Default: None",
    )
    parser.add_argument(
        "--sandbox",
        choices=["read-only", "workspace-write"],
        default=None,
        help="Sandbox mode ('read-only', 'workspace-write', or full). Default: None",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        default=True,
        help="JSONL output format (enables real-time tracking). Default: enabled",
    )
    parser.add_argument(
        "--no-output-json",
        action="store_false",
        dest="output_json",
        help="Disable JSONL output format",
    )
    parser.add_argument(
        "--full-auto",
        action="store_true",
        default=True,
        help="Enable full auto mode (required for headless). Default: enabled",
    )
    parser.add_argument(
        "--no-full-auto",
        action="store_false",
        dest="full_auto",
        help="Disable full auto mode",
    )
    parser.add_argument(
        "--image",
        action="append",
        dest="images",
        help="Image paths to include (can be specified multiple times)",
    )
    parser.add_argument(
        "--output-last-message",
        default=None,
        help="Write last message to file. Default: None",
    )
    parser.add_argument(
        "--output-schema",
        default=None,
        help="JSON schema for validation. Default: None",
    )
    parser.add_argument(
        "--skip-git-check",
        action="store_true",
        default=False,
        help="Skip git repo check. Default: False",
    )
    parser.add_argument(
        "--cd",
        dest="working_directory",
        default=None,
        help="Workspace directory. Default: None",
    )
    parser.add_argument(
        "--use-oss",
        action="store_true",
        default=False,
        help="Use local Ollama provider. Default: False",
    )
    parser.add_argument(
        "--bypass-approvals",
        action="store_true",
        default=False,
        help="Bypass approval checks. Default: False",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Max seconds to wait. Default: 120",
    )
    parser.add_argument(
        "--track",
        action="store_true",
        default=True,
        help="Enable HtmlGraph activity tracking. Default: enabled",
    )
    parser.add_argument(
        "--no-track",
        action="store_false",
        dest="track",
        help="Disable HtmlGraph activity tracking",
    )

    args = parser.parse_args()
    start_time = time.time()

    # Get parent context from environment
    parent_session = os.getenv("HTMLGRAPH_PARENT_SESSION")
    parent_event_id = os.getenv("HTMLGRAPH_PARENT_EVENT")
    parent_query_event = os.getenv("HTMLGRAPH_PARENT_QUERY_EVENT")
    parent_agent = os.getenv("HTMLGRAPH_PARENT_AGENT", "orchestrator")

    try:
        from htmlgraph.orchestration import HeadlessSpawner

        # Initialize database for event tracking
        db = None
        delegation_event_id = None
        try:
            from pathlib import Path

            from htmlgraph.db.schema import HtmlGraphDB

            # Get correct database path from environment or project root
            project_root = os.environ.get("HTMLGRAPH_PROJECT_ROOT", os.getcwd())
            db_path = Path(project_root) / ".htmlgraph" / "index.sqlite"

            if db_path.exists():
                db = HtmlGraphDB(str(db_path))
        except Exception:
            # Tracking is optional, continue without it
            pass

        # 1. RECORD DELEGATION START
        if db and args.track:
            try:
                delegation_event_id = f"event-{uuid.uuid4().hex[:8]}"
                # Use parent_query_event (UserQuery) as the root parent, with parent_event_id (task_delegation) as the intermediate parent
                db.insert_event(
                    event_id=delegation_event_id,
                    agent_id=parent_agent,
                    event_type="delegation",
                    session_id=parent_session or f"session-{uuid.uuid4().hex[:8]}",
                    tool_name="Task",
                    input_summary=args.prompt[:200],
                    context={
                        "spawned_agent": "gpt-4",
                        "spawner_type": "codex",
                        "model": args.model or "gpt-4-turbo",
                        "sandbox": args.sandbox,
                        "timeout": args.timeout,
                    },
                    parent_event_id=parent_query_event or parent_event_id,
                    subagent_type="codex",
                    cost_tokens=0,
                )

                # Record collaboration handoff
                db.record_collaboration(
                    handoff_id=f"hand-{uuid.uuid4().hex[:8]}",
                    from_agent=parent_agent,
                    to_agent="gpt-4",
                    session_id=parent_session or f"session-{uuid.uuid4().hex[:8]}",
                    handoff_type="delegation",
                    reason=args.prompt[:200],
                    context={
                        "model": args.model or "gpt-4-turbo",
                        "spawner": "codex",
                        "sandbox": args.sandbox,
                        "cost": "PAID",
                    },
                )
            except Exception:
                # Non-fatal - tracking is best-effort
                pass

        # Initialize internal activity tracker
        tracker = None
        try:
            from spawner_event_tracker import SpawnerEventTracker

            tracker = SpawnerEventTracker(
                delegation_event_id=delegation_event_id,
                parent_agent=parent_agent,
                spawner_type="codex",
                session_id=parent_session,
            )
        except Exception:
            # Tracker is optional
            pass

        # Set environment for spawned process
        os.environ["HTMLGRAPH_AGENT"] = "gpt-4"
        if delegation_event_id:
            os.environ["HTMLGRAPH_PARENT_EVENT"] = delegation_event_id

        # 2. RECORD INITIALIZATION PHASE
        init_event = None
        if tracker:
            try:
                init_event = tracker.record_phase(
                    "Initializing Codex Spawner",
                    spawned_agent="gpt-4",
                    tool_name="HeadlessSpawner.initialize",
                    input_summary=f"Preparing Codex spawner for: {args.prompt[:100]}...",
                )
            except Exception:
                pass

        # 3. RECORD SANDBOX SETUP PHASE
        sandbox_event = None
        if tracker and args.sandbox:
            try:
                sandbox_event = tracker.record_phase(
                    "Setting Up Sandbox",
                    spawned_agent="gpt-4",
                    tool_name="HeadlessSpawner.setup_sandbox",
                    input_summary=f"Sandbox mode: {args.sandbox}",
                )
            except Exception:
                pass

        # 4. EXECUTE SPAWNER
        exec_event = None
        if tracker:
            try:
                exec_event = tracker.record_phase(
                    "Executing Codex",
                    spawned_agent="gpt-4",
                    tool_name="codex-cli",
                    input_summary=args.prompt[:200],
                )
            except Exception:
                pass

        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            prompt=args.prompt,
            output_json=args.output_json,
            model=args.model,
            sandbox=args.sandbox,
            full_auto=args.full_auto,
            images=args.images,
            output_last_message=args.output_last_message,
            output_schema=args.output_schema,
            skip_git_check=args.skip_git_check,
            working_directory=args.working_directory,
            use_oss=args.use_oss,
            bypass_approvals=args.bypass_approvals,
            track_in_htmlgraph=args.track,
            timeout=args.timeout,
        )

        # 4.5 PARSE AND RECORD INTERNAL TOOL CALLS (if output_json is enabled)
        if tracker and exec_event and args.output_json:
            try:
                _parse_codex_events(
                    result.response if result.success else "",
                    tracker,
                    exec_event["event_id"],
                )
            except Exception:
                # Non-fatal - tool tracking is best-effort
                pass

        duration = time.time() - start_time

        # 5. COMPLETE EXECUTION PHASE
        if tracker and exec_event:
            try:
                output_summary = (
                    result.response[:200] if result.success else result.error[:200]
                )
                tracker.complete_phase(
                    exec_event["event_id"],
                    output_summary=output_summary,
                    status="completed" if result.success else "failed",
                )
            except Exception:
                pass

        # 6. COMPLETE SANDBOX SETUP PHASE
        if tracker and sandbox_event:
            try:
                tracker.complete_phase(
                    sandbox_event["event_id"],
                    output_summary="Sandbox configured successfully",
                    status="completed",
                )
            except Exception:
                pass

        # 7. COMPLETE INITIALIZATION PHASE
        if tracker and init_event:
            try:
                tracker.complete_phase(
                    init_event["event_id"],
                    output_summary="Codex spawner initialized successfully",
                    status="completed",
                )
            except Exception:
                pass

        # 8. TRACK COMPLETION
        if db and args.track and delegation_event_id:
            try:
                # Update event with completion metrics
                cursor = db.connection.cursor()
                cursor.execute(
                    """
                    UPDATE agent_events
                    SET output_summary = ?, status = ?, execution_duration_seconds = ?,
                        cost_tokens = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE event_id = ?
                    """,
                    (
                        (
                            result.response[:200]
                            if result.success
                            else result.error[:200]
                        ),
                        "completed" if result.success else "failed",
                        duration,
                        result.tokens_used or 0,
                        delegation_event_id,
                    ),
                )
                db.connection.commit()
            except Exception:
                # Non-fatal
                pass

        if not result.success:
            # Return JSON error to stderr
            error_output: dict[str, Any] = {
                "success": False,
                "error": result.error,
                "tokens": result.tokens_used,
                "agent": "gpt-4",
                "duration": duration,
                "delegation_event_id": delegation_event_id,
            }
            print(json.dumps(error_output), file=sys.stderr)
            sys.exit(1)

        # Return JSON success to stdout
        success_output: dict[str, Any] = {
            "success": True,
            "response": result.response,
            "tokens": result.tokens_used,
            "model": args.model,
            "sandbox": args.sandbox,
            "agent": "gpt-4",
            "duration": duration,
            "delegation_event_id": delegation_event_id,
        }
        print(json.dumps(success_output))
        sys.exit(0)

    except ImportError:
        error_output = {
            "success": False,
            "error": "HtmlGraph SDK not installed. Install with: pip install htmlgraph",
            "agent": "gpt-4",
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_output = {
            "success": False,
            "error": f"Unexpected error: {type(e).__name__}: {e}",
            "agent": "gpt-4",
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
