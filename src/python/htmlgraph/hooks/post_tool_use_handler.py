"""
PostToolUse Enhancement - Duration Calculation and Tool Trace Updates

This module handles the PostToolUse hook event and updates tool traces with:
1. Execution end time (when the tool completed)
2. Duration in milliseconds (end_time - start_time)
3. Tool output (result of the tool execution)
4. Status (Ok or Error)
5. Error message (if status is Error)

The module correlates with PreToolUse via tool_use_id environment variable
and gracefully handles missing pre-events (logs warning, continues).

Design:
- Query tool_traces for matching tool_use_id
- Get start_time from pre-event
- Calculate duration_ms (end_time - start_time)
- Update tool_traces with: end_time, duration_ms, tool_output, status, error_message
- Handle missing pre-event gracefully (log warning, continue)
- Non-blocking - errors don't prevent tool execution continuation
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from htmlgraph.db.schema import HtmlGraphDB

logger = logging.getLogger(__name__)


def calculate_duration(start_time_iso: str, end_time_iso: str) -> int:
    """
    Calculate duration in milliseconds between two ISO8601 UTC timestamps.

    Args:
        start_time_iso: ISO8601 UTC timestamp from PreToolUse (e.g., "2025-01-07T12:34:56.789000+00:00")
        end_time_iso: ISO8601 UTC timestamp (now, e.g., "2025-01-07T12:34:57.123000+00:00")

    Returns:
        duration_ms: Integer milliseconds between timestamps (accurate within 1ms)

    Raises:
        ValueError: If timestamps cannot be parsed
        TypeError: If inputs are not strings
    """
    try:
        # Parse ISO8601 timestamps (handles timezone-aware datetimes)
        start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time_iso.replace("Z", "+00:00"))

        # Calculate difference and convert to milliseconds
        delta = end_dt - start_dt
        duration_ms = int(delta.total_seconds() * 1000)

        return duration_ms
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning(f"Error calculating duration: {e}")
        raise


def update_tool_trace(
    tool_use_id: str,
    tool_output: dict[str, Any] | None,
    status: str,
    error_message: str | None = None,
) -> bool:
    """
    Update tool_traces table with execution end event.

    Updates an existing tool trace (created by PreToolUse) with:
    - end_time: Current UTC timestamp
    - duration_ms: Milliseconds between start and end
    - tool_output: Result of tool execution (JSON)
    - status: 'Ok' or 'Error'
    - error_message: Error details if status='Error'

    Args:
        tool_use_id: Correlation ID from PreToolUse event (from environment)
        tool_output: Tool execution result (dict, will be JSON serialized)
        status: 'Ok' or 'Error'
        error_message: Error details if status='Error'

    Returns:
        True if update successful, False otherwise

    Workflow:
    1. Query tool_traces for matching tool_use_id
    2. Get start_time from pre-event
    3. Calculate duration_ms (end_time - start_time)
    4. Update tool_traces with: end_time, duration_ms, tool_output, status, error_message
    5. Handle missing pre-event gracefully (log warning, continue)
    """
    try:
        # Connect to database
        db = HtmlGraphDB()

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Query tool_traces for matching tool_use_id
        cursor.execute(
            """
            SELECT tool_use_id, start_time FROM tool_traces
            WHERE tool_use_id = ?
        """,
            (tool_use_id,),
        )

        row = cursor.fetchone()

        if not row:
            # Missing pre-event - log warning but continue (graceful degradation)
            logger.warning(
                f"Could not find start event for tool_use_id={tool_use_id}. "
                f"PreToolUse event may not have completed. Skipping duration update."
            )
            db.disconnect()
            return False

        # Get start_time from pre-event
        start_time_iso = row[1]

        # Calculate end_time (now in UTC)
        end_time_iso = datetime.now(timezone.utc).isoformat()

        # Calculate duration_ms
        try:
            duration_ms = calculate_duration(start_time_iso, end_time_iso)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Could not calculate duration for tool_use_id={tool_use_id}: {e}. "
                f"Using None for duration."
            )
            duration_ms = None

        # Validate status
        valid_statuses = {"Ok", "Error", "completed", "failed", "timeout"}
        if status not in valid_statuses:
            logger.warning(
                f"Invalid status '{status}' for tool_use_id={tool_use_id}. "
                f"Using 'Ok' as default."
            )
            status = "Ok"

        # JSON serialize tool_output
        tool_output_json = None
        if tool_output:
            try:
                tool_output_json = json.dumps(tool_output)
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Could not JSON serialize tool_output for "
                    f"tool_use_id={tool_use_id}: {e}"
                )
                tool_output_json = json.dumps(
                    {"error": str(e), "output": str(tool_output)}
                )

        # Update tool_traces with: end_time, duration_ms, tool_output, status, error_message
        cursor.execute(
            """
            UPDATE tool_traces
            SET end_time = ?, duration_ms = ?, tool_output = ?,
                status = ?, error_message = ?
            WHERE tool_use_id = ?
        """,
            (
                end_time_iso,
                duration_ms,
                tool_output_json,
                status,
                error_message,
                tool_use_id,
            ),
        )

        if not db.connection:
            db.connect()

        db.connection.commit()  # type: ignore[union-attr]

        logger.debug(
            f"Updated tool trace: tool_use_id={tool_use_id}, "
            f"duration_ms={duration_ms}, status={status}"
        )

        db.disconnect()
        return True

    except Exception as e:
        # Log error but don't block
        logger.error(f"Error updating tool trace for tool_use_id={tool_use_id}: {e}")
        return False


def get_tool_use_id_from_context() -> str | None:
    """
    Get tool_use_id from environment (set by PreToolUse hook).

    Returns:
        tool_use_id string or None if not set
    """
    return os.environ.get("HTMLGRAPH_TOOL_USE_ID")


def determine_status_from_response(
    tool_response: dict[str, Any] | None,
) -> tuple[str, str | None]:
    """
    Determine status (Ok/Error) and error message from tool response.

    Analyzes tool response to determine if execution was successful.
    Returns (status, error_message) tuple.

    Args:
        tool_response: Tool execution response (dict)

    Returns:
        (status, error_message) where:
        - status: 'Ok' or 'Error'
        - error_message: Error details if Error, else None
    """
    if not tool_response:
        return ("Ok", None)

    if not isinstance(tool_response, dict):
        return ("Ok", None)

    # Check for explicit error indicators
    # Bash tool: non-empty stderr
    stderr = tool_response.get("stderr", "")
    if stderr and isinstance(stderr, str) and stderr.strip():
        return ("Error", f"stderr: {stderr[:500]}")

    # Explicit error field
    error_field = tool_response.get("error")
    if error_field and str(error_field).strip():
        return ("Error", str(error_field)[:500])

    # success=false flag
    if tool_response.get("success") is False:
        reason = tool_response.get("reason", "Unknown error")
        return ("Error", str(reason)[:500])

    # status field indicating failure
    status_field = tool_response.get("status")
    if status_field and status_field.lower() in {"error", "failed", "failed"}:
        reason = tool_response.get("message", "Unknown error")
        return ("Error", str(reason)[:500])

    # Default to success
    return ("Ok", None)
