#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

"""
PostToolUseFailure Hook - Automatic Error Tracking and Debug Spike Creation

This hook is triggered when tool executions fail, enabling:
- Error logging to .htmlgraph/errors.jsonl
- Pattern detection for recurring errors (3+ occurrences)
- Automatic debug spike creation for investigation
- Error context preservation for debugging

CRITICAL REQUIREMENTS:
- MUST exit with code 0 (exit 1 blocks Claude)
- MUST execute quickly (< 1 second)
- MUST use file-based output (not stdout)
- MUST handle all exceptions gracefully
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def run(hook_input: dict[str, Any]) -> dict[str, Any]:
    """
    Handle tool execution failures.

    Args:
        hook_input: Hook input containing:
            - name: Tool name that failed
            - result: Tool result (may contain error field)
            - session_id: Current session ID

    Returns:
        Standard hook response: {"continue": True}
    """
    try:
        # DEBUG: Log raw hook input to understand structure
        debug_log = Path(".htmlgraph/hook-debug.jsonl")
        debug_log.parent.mkdir(parents=True, exist_ok=True)
        with open(debug_log, "a") as f:
            f.write(
                json.dumps(
                    {
                        "raw_input": hook_input,
                        "keys": list(hook_input.keys()),
                        "ts": datetime.now().isoformat(),
                    }
                )
                + "\n"
            )

        # Extract error information from PostToolUse hook format
        # Official PostToolUse uses: tool_name, tool_response
        # Custom hooks may use: name, result
        tool_name = hook_input.get("tool_name") or hook_input.get("name", "unknown")
        session_id = hook_input.get("session_id", "unknown")

        # Error message can be in different places depending on tool
        error_msg = "No error message"

        # Check tool_response field first (official PostToolUse format)
        # Then check result field (custom hook format)
        result = hook_input.get("tool_response") or hook_input.get("result", {})
        if isinstance(result, dict):
            if "error" in result:
                error_msg = result["error"]
            elif "message" in result:
                error_msg = result["message"]
        elif isinstance(result, str):
            # Sometimes the error is directly in the result as a string
            error_msg = result

        # Fallback: check top-level error field
        if error_msg == "No error message" and "error" in hook_input:
            error_msg = hook_input["error"]

        # Last resort: stringify the result if it contains error indicators
        if error_msg == "No error message" and result:
            result_str = str(result).lower()
            if any(
                indicator in result_str
                for indicator in ["error", "failed", "exception"]
            ):
                error_msg = str(result)[:500]  # Truncate to 500 chars

        # Track error in file-based storage
        error_log = Path(".htmlgraph/errors.jsonl")
        error_log.parent.mkdir(parents=True, exist_ok=True)

        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "error": error_msg,
            "session_id": session_id,
        }

        with open(error_log, "a") as f:
            f.write(json.dumps(error_entry) + "\n")

        # Check for error patterns (same error 3+ times)
        if should_create_debug_spike(tool_name, error_msg, error_log):
            create_debug_spike(tool_name, error_msg, error_log)

        # Return success (don't block Claude)
        return {"continue": True}

    except Exception as e:
        # Never raise - log and continue
        logger.warning(f"PostToolUseFailure hook error: {e}")
        return {"continue": True}


def should_create_debug_spike(tool: str, error: str, log_path: Path) -> bool:
    """
    Check if this error has occurred 3+ times.

    Args:
        tool: Tool name that failed
        error: Error message
        log_path: Path to errors.jsonl

    Returns:
        True if error occurred 3+ times, False otherwise
    """
    if not log_path.exists():
        return False

    count = 0
    # Use first 100 chars of error for pattern matching
    error_signature = error[:100]

    with open(log_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("tool") == tool and error_signature in entry.get(
                    "error", ""
                ):
                    count += 1
                    if count >= 3:
                        return True
            except Exception:
                continue
    return False


def create_debug_spike(tool: str, error: str, log_path: Path) -> None:
    """
    Auto-create debug spike for recurring error.

    Args:
        tool: Tool name that failed
        error: Error message
        log_path: Path to errors.jsonl
    """
    try:
        from htmlgraph import SDK

        sdk = SDK(agent="error-tracker")

        # Get recent occurrences
        occurrences = []
        error_signature = error[:100]
        with open(log_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("tool") == tool and error_signature in entry.get(
                        "error", ""
                    ):
                        occurrences.append(entry)
                except Exception:
                    continue

        # Check if spike already exists for this error
        spike_marker = Path(".htmlgraph/.error-spikes.json")
        existing_spikes = {}
        if spike_marker.exists():
            try:
                with open(spike_marker) as f:
                    existing_spikes = json.load(f)
            except Exception:
                pass

        # Create unique key for this error
        error_key = f"{tool}:{error_signature}"
        if error_key in existing_spikes:
            # Already created spike for this error
            return

        # Create debug spike
        spike = (
            sdk.spikes.create(f"Recurring Error: {tool}")
            .set_spike_type("technical")
            .set_findings(
                f"""
## Recurring Tool Failure Detected

**Tool**: {tool}
**Occurrences**: {len(occurrences)}
**First Seen**: {occurrences[0]["timestamp"] if occurrences else "unknown"}
**Last Seen**: {occurrences[-1]["timestamp"] if occurrences else "unknown"}

### Error Message
```
{error}
```

### Recent Occurrences
{chr(10).join(f"- {o['timestamp']}: {o.get('session_id', 'unknown')}" for o in occurrences[-5:])}

### Recommended Actions
1. Review error message for root cause
2. Check if this is a known issue in the codebase
3. Search GitHub issues if Claude Code related
4. Fix underlying issue or add error handling
5. Test fix to ensure error doesn't recur

### Debugging Resources
- `.htmlgraph/errors.jsonl` - Full error log
- `DEBUGGING.md` - Systematic debugging guide
- `/doctor` - System diagnostics
- `claude --debug` - Verbose output
            """
            )
            .save()
        )

        # Record that we created a spike for this error
        existing_spikes[error_key] = {
            "spike_id": spike.id,
            "created": datetime.now().isoformat(),
            "occurrences": len(occurrences),
        }
        with open(spike_marker, "w") as f:
            json.dump(existing_spikes, f, indent=2)

        logger.warning(f"Created debug spike: {spike.id}")

    except Exception as e:
        logger.warning(f"Failed to create debug spike: {e}")


def main() -> None:
    """Hook entry point for script wrapper."""
    # Check environment override
    if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Read tool input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Run hook
    result = run(hook_input)

    # Output response
    print(json.dumps(result))
    sys.exit(0)  # Always exit 0


if __name__ == "__main__":
    main()
