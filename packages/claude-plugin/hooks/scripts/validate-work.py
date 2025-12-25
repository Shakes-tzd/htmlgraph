#!/usr/bin/env python3
"""
Pre-Work Validation Hook

Enforces HtmlGraph workflow by requiring active work items for code changes.

Core Principles:
1. SDK is the ONLY interface to .htmlgraph/ - never direct Write/Edit
2. ALL spikes (auto-generated and manual) are for planning only:
   - Allow: Read operations, SDK commands, running tests
   - Deny: Write, Edit, Delete (code changes)
   - File creation/editing only in .htmlgraph/ via SDK Bash commands
3. Features/bugs/chores are for code implementation

Hook Input (stdin): JSON with tool call details
Hook Output (stdout): JSON permission decision {"decision": "allow|deny", "reason": "...", "suggestion": "..."}
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _resolve_project_dir(cwd: Optional[str] = None) -> str:
    """Resolve project directory (git root or cwd)."""
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return env_dir
    start_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=start_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return start_dir


def _bootstrap_pythonpath(project_dir: str) -> None:
    """Add local virtualenv and src paths to Python path."""
    venv = Path(project_dir) / ".venv"
    if venv.exists():
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            venv / "lib" / pyver / "site-packages",
            venv / "Lib" / "site-packages",
        ]
        for c in candidates:
            if c.exists():
                sys.path.insert(0, str(c))

    repo_src = Path(project_dir) / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


# Bootstrap PYTHONPATH for local development
project_dir_for_import = _resolve_project_dir()
_bootstrap_pythonpath(project_dir_for_import)


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


def validate_tool_call(tool: str, params: dict, config: dict) -> dict:
    """
    Validate tool call and return permission decision.

    Returns:
        dict: {"decision": "allow|deny", "reason": "...", "suggestion": "..."}
    """
    templates = config.get("permission_responses", {}).get("templates", {})

    # Step 1: Always allow read-only tools
    if is_always_allowed(tool, params, config):
        return templates.get("read_only_allowed", {
            "decision": "allow",
            "reason": "Read-only operation"
        })

    # Step 2: Always deny direct writes to .htmlgraph/
    is_htmlgraph_write, file_path = is_direct_htmlgraph_write(tool, params)
    if is_htmlgraph_write:
        template = templates.get("direct_htmlgraph_write_denied", {})
        return {
            "decision": "deny",
            "reason": template.get("reason", "Direct writes to .htmlgraph/ are forbidden"),
            "suggestion": template.get("suggestion", "Use SDK: uv run htmlgraph feature create")
        }

    # Step 3: Classify operation
    is_sdk_cmd = is_sdk_command(tool, params, config)
    is_code_op = is_code_operation(tool, params, config)

    # Step 4: Get active work item
    active = get_active_work_item()

    # Step 5: No active work item
    if active is None:
        if is_sdk_cmd:
            # Creating work items is OK
            return templates.get("sdk_command_no_work", {
                "decision": "allow",
                "reason": "Creating work item via SDK"
            })

        if is_code_op or tool in ["Write", "Edit", "Delete"]:
            # Code changes require work item
            template = templates.get("no_work_item_code_change", {})
            return {
                "decision": "deny",
                "reason": template.get("reason", "No active work item"),
                "suggestion": template.get("suggestion", "Create a work item first")
            }

        # Other operations allowed
        return {
            "decision": "allow",
            "reason": "Exploratory operation"
        }

    # Step 6: Active work is a spike (planning only - ALL spikes)
    # ALL spikes (auto-generated and manual) enforce planning-only rules:
    # - Allow: Read operations, SDK commands, running tests
    # - Deny: Write, Edit, Delete (code changes)
    # - File creation/editing only in .htmlgraph/ via SDK Bash commands
    if active.get("type") == "spike":
        spike_id = active.get("id")

        if is_sdk_cmd:
            # Planning: creating work items via SDK is OK
            template = templates.get("sdk_command_with_spike", {})
            reason = template.get("reason", "Planning with spike: creating work items via SDK")
            return {
                "decision": "allow",
                "reason": reason.format(spike_id=spike_id)
            }

        if tool in ["Write", "Edit", "Delete", "NotebookEdit"] or is_code_op:
            # Code changes require feature/bug/chore
            template = templates.get("spike_code_change_denied", {})
            reason = template.get("reason", "Spike is for planning only")
            suggestion = template.get("suggestion", "Create a feature for code changes")
            return {
                "decision": "deny",
                "reason": reason.format(spike_id=spike_id),
                "suggestion": suggestion
            }

        # Other operations (exploratory) allowed
        return {
            "decision": "allow",
            "reason": f"Exploratory operation with spike {spike_id}"
        }

    # Step 7: Active work is feature/bug/chore - allow code operations
    work_item_id = active.get("id")
    template = templates.get("implementation_work_active", {})
    reason = template.get("reason", "Active implementation work")
    return {
        "decision": "allow",
        "reason": reason.format(work_item_id=work_item_id)
    }


def main():
    """Main entry point."""
    try:
        # Read tool input from stdin
        tool_input = json.load(sys.stdin)

        tool = tool_input.get("tool", "")
        params = tool_input.get("params", {})

        # Load config
        config = load_validation_config()

        # Validate and get permission decision
        decision = validate_tool_call(tool, params, config)

        # Output JSON decision
        print(json.dumps(decision))

        # Exit with appropriate code
        if decision.get("decision") == "deny":
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        # Graceful degradation - allow on error
        print(json.dumps({
            "decision": "allow",
            "reason": f"Validation hook error: {e}"
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()
