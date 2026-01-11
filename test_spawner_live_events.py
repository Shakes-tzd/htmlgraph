#!/usr/bin/env python3
"""
Test script to generate live spawner events for dashboard observation.

This script:
1. Creates a spawner task that takes 10-15 seconds
2. Generates delegation events via LiveEventPublisher
3. Broadcasts to WebSocket connections on the dashboard
4. Provides real-time activity feed updates
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.orchestration.live_events import LiveEventPublisher


def main():
    """Execute exploration task that generates live spawner events."""

    print("=" * 70)
    print("SPAWNER LIVE EVENT GENERATOR")
    print("=" * 70)
    print()

    # Get project root
    project_root = Path(__file__).parent
    db_path = project_root / ".htmlgraph" / "index.sqlite"

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        print("Please ensure .htmlgraph/ directory is initialized")
        return 1

    print(f"Using database: {db_path}")
    print()

    # Initialize database and event publisher
    db = HtmlGraphDB(str(db_path))
    live_publisher = LiveEventPublisher()

    # Set environment for spawned agents
    os.environ["HTMLGRAPH_PROJECT_ROOT"] = str(project_root)

    # Create a session for this exploration task
    session_id = f"session-live-explore-{int(time.time())}"
    print(f"Session ID: {session_id}")
    print()

    start_time = time.time()

    try:
        # 1. Record task start event
        print("[1/5] Recording task delegation event...")
        task_event_id = f"event-delegation-{int(time.time())}"

        db.insert_event(
            event_id=task_event_id,
            agent_id="claude",
            event_type="delegation",
            session_id=session_id,
            tool_name="Task",
            input_summary="Analyze HtmlGraph codebase structure and count modules",
            output_summary="Starting exploration...",
            context={
                "spawned_agent": "gemini-2.0-flash",
                "spawner_type": "gemini",
                "model": "gemini-2.0-flash",
                "cost": "FREE",
                "task_type": "exploratory_analysis",
            },
            subagent_type="gemini",
            cost_tokens=0,
        )

        # Publish live event: delegation started
        live_publisher.spawner_start(
            spawner_type="gemini",
            prompt="Analyze HtmlGraph codebase structure",
            parent_event_id=task_event_id,
            model="gemini-2.0-flash",
            session_id=session_id,
        )

        print(f"  ✓ Delegation event created: {task_event_id}")
        time.sleep(2)

        # 2. Record initialization phase
        print("[2/5] Publishing initialization phase...")
        init_event_id = f"event-init-{int(time.time())}"

        db.insert_event(
            event_id=init_event_id,
            agent_id="gemini-2.0-flash",
            event_type="phase",
            session_id=session_id,
            tool_name="HeadlessSpawner.initialize",
            input_summary="Preparing Gemini spawner environment",
            output_summary="Initialization in progress",
            context={
                "phase": "initialization",
                "spawner": "gemini",
                "parent_event": task_event_id,
            },
            parent_event_id=task_event_id,
            cost_tokens=0,
        )

        live_publisher.spawner_phase(
            spawner_type="gemini",
            phase="initializing",
            details="Setting up Gemini spawner environment and context",
            parent_event_id=task_event_id,
            session_id=session_id,
        )

        print(f"  ✓ Initialization phase: {init_event_id}")
        time.sleep(2)

        # 3. Complete initialization and record execution phase
        print("[3/5] Publishing execution phase...")

        # Complete init
        cursor = db.connection.cursor()
        cursor.execute(
            """
            UPDATE agent_events
            SET output_summary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ?
            """,
            ("Spawner environment ready", init_event_id),
        )
        db.connection.commit()

        # Start execution phase
        exec_event_id = f"event-exec-{int(time.time())}"

        db.insert_event(
            event_id=exec_event_id,
            agent_id="gemini-2.0-flash",
            event_type="phase",
            session_id=session_id,
            tool_name="gemini-cli",
            input_summary="Executing codebase analysis with Gemini 2.0-Flash",
            output_summary="Execution in progress",
            context={
                "phase": "execution",
                "spawner": "gemini",
                "model": "gemini-2.0-flash",
                "parent_event": task_event_id,
            },
            parent_event_id=task_event_id,
            cost_tokens=0,
        )

        live_publisher.spawner_phase(
            spawner_type="gemini",
            phase="executing",
            details="Running Gemini 2.0-Flash for exploratory analysis...",
            parent_event_id=task_event_id,
            session_id=session_id,
        )

        print(f"  ✓ Execution phase started: {exec_event_id}")
        time.sleep(3)

        # 4. Simulate work with intermediate updates
        print("[4/5] Publishing intermediate progress updates...")

        for i, step in enumerate(
            [
                "Scanning src/python/htmlgraph/ directory structure",
                "Analyzing main module imports and dependencies",
                "Counting files in SDK, API, CLI, and orchestration modules",
                "Generating analysis report and recommendations",
            ],
            1,
        ):
            tool_event_id = f"event-tool-{int(time.time())}-{i}"

            db.insert_event(
                event_id=tool_event_id,
                agent_id="gemini-2.0-flash",
                event_type="tool_call",
                session_id=session_id,
                tool_name="bash",
                input_summary=step,
                output_summary=f"Executing: {step}",
                context={
                    "step": i,
                    "total_steps": 4,
                    "parent_execution": exec_event_id,
                },
                parent_event_id=exec_event_id,
                cost_tokens=0,
            )

            print(f"    Step {i}: {step}")
            time.sleep(2.5)

            # Complete the tool call
            cursor.execute(
                """
                UPDATE agent_events
                SET output_summary = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE event_id = ?
                """,
                (f"Completed: {step}", tool_event_id),
            )
            db.connection.commit()

        time.sleep(2)

        # 5. Complete execution and record final analysis
        print("[5/5] Publishing completion event...")

        analysis_result = """
        CODEBASE ANALYSIS RESULTS:

        Main Modules Found:
        - SDK Module: 8 files (sdk.py, models.py, query_builder.py, etc.)
        - API Module: 12 files (server.py, routes.py, handlers.py, etc.)
        - CLI Module: 6 files (cli.py, commands.py, output.py, etc.)
        - Orchestration: 14 files (spawner.py, live_events.py, delegation.py, etc.)
        - Database: 10 files (schema.py, migrations.py, queries.py, etc.)
        - Archive: 4 files (manager.py, fts.py, search.py, bloom.py)

        Total: 54 Python files analyzed
        Key Dependencies: sqlite3, pathlib, uuid, json, subprocess
        """

        # Complete execution phase
        cursor.execute(
            """
            UPDATE agent_events
            SET output_summary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE event_id = ?
            """,
            (analysis_result[:200], exec_event_id),
        )
        db.connection.commit()

        # Complete delegation event
        duration = time.time() - start_time
        cursor.execute(
            """
            UPDATE agent_events
            SET output_summary = ?,
                execution_duration_seconds = ?
            WHERE event_id = ?
            """,
            (analysis_result[:200], duration, task_event_id),
        )
        db.connection.commit()

        # Publish completion event
        live_publisher.spawner_complete(
            spawner_type="gemini",
            success=True,
            duration_seconds=duration,
            response_preview=analysis_result[:200],
            tokens_used=450,
            parent_event_id=task_event_id,
            session_id=session_id,
        )

        print(f"  ✓ Task completed in {duration:.1f} seconds")
        print()
        print("=" * 70)
        print("LIVE EVENTS PUBLISHED")
        print("=" * 70)
        print()
        print(f"Total Duration: {duration:.1f} seconds")
        print(f"Session ID: {session_id}")
        print(
            "Events Generated: 1 delegation + 1 init + 1 exec + 4 tool calls + 1 completion = 8 events"
        )
        print()
        print("Check the dashboard at: http://localhost:8000")
        print("Activity feed should show all events in real-time")
        print()

        return 0

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.connection.close()


if __name__ == "__main__":
    sys.exit(main())
