#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
Pre-Work Validation Hook (GUIDANCE MODE) with Active Learning

Provides intelligent guidance for HtmlGraph workflow based on:
1. Current workflow state (work items, spikes)
2. Recent tool usage patterns (anti-pattern detection)
3. Learned patterns from transcript analytics

Philosophy:
- Hooks GUIDE agents with suggestions, they do NOT block
- Learn from past patterns to provide smarter guidance
- Trust the agent to make good decisions
- Active feedback loop improves agent workflows

Hook Input (stdin): JSON with tool call details
Hook Output (stdout): JSON with guidance {"decision": "allow", "guidance": "...", "suggestion": "..."}
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# Anti-patterns to detect (tool sequence -> warning message)
ANTI_PATTERNS = {
    ("Bash", "Bash", "Bash", "Bash"): "4 consecutive Bash commands. Check for errors or consider a different approach.",
    ("Edit", "Edit", "Edit"): "3 consecutive Edits. Consider batching changes or reading file first.",
    ("Grep", "Grep", "Grep"): "3 consecutive Greps. Consider reading results before searching more.",
    ("Read", "Read", "Read", "Read"): "4 consecutive Reads. Consider caching file content.",
}

# Optimal patterns to encourage
OPTIMAL_PATTERNS = {
    ("Grep", "Read"): "Good: Search then read - efficient exploration.",
    ("Read", "Edit"): "Good: Read then edit - informed changes.",
    ("Edit", "Bash"): "Good: Edit then test - verify changes.",
}

# Session tool history file
TOOL_HISTORY_FILE = Path("/tmp/htmlgraph-tool-history.json")
MAX_HISTORY = 20


def load_tool_history() -> list[dict]:
    """Load recent tool history from temp file."""
    if TOOL_HISTORY_FILE.exists():
        try:
            data = json.loads(TOOL_HISTORY_FILE.read_text())
            # Filter to last hour only
            cutoff = datetime.now().timestamp() - 3600
            return [t for t in data if t.get("ts", 0) > cutoff][-MAX_HISTORY:]
        except Exception:
            pass
    return []


def save_tool_history(history: list[dict]) -> None:
    """Save tool history to temp file."""
    try:
        TOOL_HISTORY_FILE.write_text(json.dumps(history[-MAX_HISTORY:]))
    except Exception:
        pass


def record_tool(tool: str, history: list[dict]) -> list[dict]:
    """Record a tool use in history."""
    history.append({
        "tool": tool,
        "ts": datetime.now().timestamp()
    })
    return history[-MAX_HISTORY:]


def detect_anti_pattern(tool: str, history: list[dict]) -> Optional[str]:
    """Check if adding this tool creates an anti-pattern."""
    recent_tools = [h["tool"] for h in history[-4:]] + [tool]

    for pattern, message in ANTI_PATTERNS.items():
        pattern_len = len(pattern)
        if len(recent_tools) >= pattern_len:
            # Check if recent tools end with this pattern
            if tuple(recent_tools[-pattern_len:]) == pattern:
                return message

    return None


def detect_optimal_pattern(tool: str, history: list[dict]) -> Optional[str]:
    """Check if this tool continues an optimal pattern."""
    if not history:
        return None

    last_tool = history[-1]["tool"]
    pair = (last_tool, tool)

    return OPTIMAL_PATTERNS.get(pair)


def get_pattern_guidance(tool: str, history: list[dict]) -> dict:
    """Get guidance based on tool patterns."""
    # Check for anti-patterns first
    anti_pattern = detect_anti_pattern(tool, history)
    if anti_pattern:
        return {
            "pattern_warning": f"⚠️ {anti_pattern}",
            "pattern_type": "anti-pattern"
        }

    # Check for optimal patterns
    optimal = detect_optimal_pattern(tool, history)
    if optimal:
        return {
            "pattern_note": optimal,
            "pattern_type": "optimal"
        }

    return {}


def get_session_health_hint(history: list[dict]) -> Optional[str]:
    """Get a health hint based on session patterns."""
    if len(history) < 10:
        return None

    tools = [h["tool"] for h in history]

    # Check for excessive retries
    consecutive = 1
    max_consecutive = 1
    for i in range(1, len(tools)):
        if tools[i] == tools[i-1]:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 1

    if max_consecutive >= 5:
        return f"📊 High retry pattern detected ({max_consecutive} consecutive same-tool calls). Consider varying approach."

    # Check tool diversity
    unique_tools = len(set(tools))
    if unique_tools <= 2 and len(tools) >= 10:
        return f"📊 Low tool diversity. Only using {unique_tools} different tools. Consider using more specialized tools."

    return None


def load_validation_config() -> dict:
    """Load validation config with defaults."""
    config_path = Path(__file__).parent.parent.parent / "config" / "validation-config.json"

    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            pass

    # Minimal fallback config
    return {
        "always_allow": {
            "tools": ["Read", "Glob", "Grep", "LSP"],
            "bash_patterns": ["^git status", "^git diff", "^ls", "^cat"]
        },
        "sdk_commands": {
            "patterns": ["^uv run htmlgraph ", "^htmlgraph "]
        }
    }


def is_always_allowed(tool: str, params: dict, config: dict) -> bool:
    """Check if tool is always allowed (read-only operations)."""
    # Always-allow tools
    if tool in config.get("always_allow", {}).get("tools", []):
        return True

    # Read-only Bash patterns
    if tool == "Bash":
        command = params.get("command", "")
        for pattern in config.get("always_allow", {}).get("bash_patterns", []):
            if re.match(pattern, command):
                return True

    return False


def is_direct_htmlgraph_write(tool: str, params: dict) -> tuple[bool, str]:
    """Check if attempting direct write to .htmlgraph/ (always denied)."""
    if tool not in ["Write", "Edit", "Delete", "NotebookEdit"]:
        return False, ""

    file_path = params.get("file_path", "")
    if ".htmlgraph/" in file_path or file_path.startswith(".htmlgraph/"):
        return True, file_path

    return False, ""


def is_sdk_command(tool: str, params: dict, config: dict) -> bool:
    """Check if Bash command is an SDK command."""
    if tool != "Bash":
        return False

    command = params.get("command", "")
    for pattern in config.get("sdk_commands", {}).get("patterns", []):
        if re.match(pattern, command):
            return True

    return False


def is_code_operation(tool: str, params: dict, config: dict) -> bool:
    """Check if operation modifies code."""
    # Direct file operations
    if tool in config.get("code_operations", {}).get("tools", []):
        return True

    # Code-modifying Bash commands
    if tool == "Bash":
        command = params.get("command", "")
        for pattern in config.get("code_operations", {}).get("bash_patterns", []):
            if re.match(pattern, command):
                return True

    return False


def get_active_work_item() -> Optional[dict]:
    """Get active work item using SDK."""
    try:
        from htmlgraph import SDK

        sdk = SDK()
        active = sdk.get_active_work_item()
        return active
    except Exception:
        # If SDK fails, assume no active work item
        return None


def validate_tool_call(tool: str, params: dict, config: dict, history: list[dict]) -> dict:
    """
    Validate tool call and return GUIDANCE with active learning.

    Returns:
        dict: {"decision": "allow", "guidance": "...", "suggestion": "...", ...}
              All operations are ALLOWED - guidance is informational only.
    """
    result = {"decision": "allow"}
    guidance_parts = []

    # Step 0: Check for pattern-based guidance (Active Learning)
    pattern_info = get_pattern_guidance(tool, history)
    if pattern_info.get("pattern_warning"):
        guidance_parts.append(pattern_info["pattern_warning"])

    # Check session health
    health_hint = get_session_health_hint(history)
    if health_hint:
        guidance_parts.append(health_hint)

    # Step 1: Read-only tools - minimal guidance
    if is_always_allowed(tool, params, config):
        if guidance_parts:
            result["guidance"] = " | ".join(guidance_parts)
        return result

    # Step 2: Direct writes to .htmlgraph/ - BLOCK (not guidance)
    # This is the ONLY blocking rule - all other rules are guidance only
    is_htmlgraph_write, file_path = is_direct_htmlgraph_write(tool, params)
    if is_htmlgraph_write:
        # Return blocking response - this will be handled specially
        return {
            "decision": "block",
            "reason": f"BLOCKED: Direct edits to .htmlgraph/ files are not allowed. File: {file_path}",
            "suggestion": "Use SDK instead: `from htmlgraph import SDK; sdk = SDK(); sdk.features.complete('id')`",
            "documentation": "See AGENTS.md line 3: 'AI agents must NEVER edit .htmlgraph/ HTML files directly'"
        }

    # Step 3: Classify operation
    is_sdk_cmd = is_sdk_command(tool, params, config)
    is_code_op = is_code_operation(tool, params, config)

    # Step 4: Get active work item
    active = get_active_work_item()

    # Step 5: No active work item
    if active is None:
        if is_sdk_cmd:
            guidance_parts.append("Creating work item via SDK")
        elif is_code_op or tool in ["Write", "Edit", "Delete"]:
            guidance_parts.append("No active work item. Consider creating one to track this work.")
            result["suggestion"] = "uv run htmlgraph feature create 'Feature title'"

        if guidance_parts:
            result["guidance"] = " | ".join(guidance_parts)
        return result

    # Step 6: Active work is a spike (planning phase)
    if active.get("type") == "spike":
        spike_id = active.get("id")

        if is_sdk_cmd:
            guidance_parts.append(f"Planning with spike {spike_id}")
        elif tool in ["Write", "Edit", "Delete", "NotebookEdit"] or is_code_op:
            guidance_parts.append(f"Active spike ({spike_id}) is for planning. Consider creating a feature for implementation.")
            result["suggestion"] = "uv run htmlgraph feature create 'Feature title'"

        if guidance_parts:
            result["guidance"] = " | ".join(guidance_parts)
        return result

    # Step 7: Active work is feature/bug/chore - all good
    work_item_id = active.get("id")
    guidance_parts.append(f"Working on {work_item_id}")

    # Add positive reinforcement for optimal patterns
    if pattern_info.get("pattern_note"):
        guidance_parts.append(pattern_info["pattern_note"])

    if guidance_parts:
        result["guidance"] = " | ".join(guidance_parts)

    return result


def main():
    """Main entry point."""
    try:
        # Read tool input from stdin
        tool_input = json.load(sys.stdin)

        tool = tool_input.get("tool", "")
        params = tool_input.get("params", {})

        # Load config
        config = load_validation_config()

        # Load and update tool history (Active Learning)
        history = load_tool_history()

        # Get guidance with pattern awareness
        result = validate_tool_call(tool, params, config, history)

        # Record this tool in history (for next call)
        history = record_tool(tool, history)
        save_tool_history(history)

        # Output JSON with guidance/block message
        print(json.dumps(result))

        # Exit 1 to BLOCK if decision is "block", otherwise allow
        if result.get("decision") == "block":
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        # Graceful degradation - allow on error
        print(json.dumps({
            "decision": "allow",
            "guidance": f"Validation hook error: {e}"
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()
