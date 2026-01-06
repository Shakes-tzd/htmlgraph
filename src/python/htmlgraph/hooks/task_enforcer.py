"""
Task Enforcer - Auto-inject HtmlGraph save instructions into Task prompts.

This module provides PreToolUse enforcement for the Task tool, ensuring that
subagent prompts include instructions to save their findings to HtmlGraph.

Architecture:
- Detects Task tool calls in PreToolUse hook
- Checks if prompt already includes save instructions
- Auto-injects SDK save template if missing
- Returns updatedInput with modified prompt
- Tracks parent session context and nesting depth (Phase 2)

Usage:
    from htmlgraph.hooks.task_enforcer import enforce_task_saving

    result = enforce_task_saving(tool_name, tool_params)
    # Returns: {"continue": True, "hookSpecificOutput": {"updatedInput": {...}}}
"""

import os
from typing import Any


def has_save_instructions(prompt: str) -> bool:
    """
    Check if prompt already includes HtmlGraph save instructions.

    Args:
        prompt: Task prompt to check

    Returns:
        True if save instructions are present, False otherwise
    """
    # Keywords that indicate save instructions are already present
    save_keywords = [
        "sdk",
        "htmlgraph",
        ".save()",
        "spike",
        "report results",
        "save findings",
        "track results",
    ]

    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in save_keywords)


def inject_save_instructions(prompt: str, subagent_type: str = "haiku") -> str:
    """
    Inject HtmlGraph save instructions into Task prompt.

    Args:
        prompt: Original task prompt
        subagent_type: Type of subagent (default: "haiku")

    Returns:
        Modified prompt with save instructions appended
    """
    # Template to inject
    save_template = f"""

🔴 CRITICAL - Report Results to HtmlGraph:
After completing your research/analysis, you MUST save your findings using:

```python
from htmlgraph import SDK
sdk = SDK(agent='{subagent_type}')
spike = sdk.spikes.create('Your Task Summary Here')
spike.set_findings(\'\'\'
# Your Comprehensive Findings

## Summary
[Brief overview of what you discovered]

## Key Findings
- [Finding 1]
- [Finding 2]
- [Finding 3]

## Details
[Detailed analysis, code examples, etc.]

## Recommendations
[Action items or next steps]
\'\'\')
spike.save()
```

IMPORTANT:
- Replace 'Your Task Summary Here' with a concise description of your task
- Include ALL relevant findings in the set_findings() call
- This creates a permanent record that can be referenced later
- The spike will be saved to .htmlgraph/spikes/ directory
"""

    return prompt + save_template


def enforce_task_saving(tool_name: str, tool_params: dict[str, Any]) -> dict[str, Any]:
    """
    Enforce HtmlGraph result saving for Task tool calls.

    Args:
        tool_name: Name of the tool being called
        tool_params: Tool parameters (includes "prompt" for Task)

    Returns:
        Hook response with updatedInput if modifications needed:
        {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {...},  # Modified tool_params
                "additionalContext": "..."  # Optional guidance
            }
        }
    """
    # Only process Task tool calls
    if tool_name != "Task":
        return {"continue": True}

    # Get prompt from tool params
    prompt = tool_params.get("prompt", "")
    if not prompt:
        return {"continue": True}

    # Phase 2: Track parent session context and increment nesting depth
    parent_session = os.environ.get("HTMLGRAPH_PARENT_SESSION")
    parent_agent = os.environ.get("HTMLGRAPH_PARENT_AGENT", "claude-code")
    nesting_depth = int(os.environ.get("HTMLGRAPH_NESTING_DEPTH", "0"))
    current_session = os.environ.get("HTMLGRAPH_SESSION_ID", "")

    # Record delegation event in database
    try:
        import uuid

        from htmlgraph.db.schema import HtmlGraphDB

        db = HtmlGraphDB()
        db.connect()

        # Extract to_agent from subagent_type (e.g., "haiku" -> "haiku", "gemini-spawner" -> "gemini-spawner")
        to_agent = tool_params.get("subagent_type", "unknown")
        task_description = tool_params.get("description", "Unnamed task")

        # Determine session ID, using current > parent > auto-generated
        session_id = (
            current_session or parent_session or f"session-{uuid.uuid4().hex[:8]}"
        )

        # Ensure session exists before recording delegation (handles FK constraints)
        db._ensure_session_exists(session_id, parent_agent)

        # Record the delegation event
        db.record_delegation_event(
            from_agent=parent_agent,
            to_agent=to_agent,
            task_description=task_description,
            session_id=session_id,
            context={
                "nesting_depth": nesting_depth,
                "prompt_preview": prompt[:200] if prompt else "",
            },
        )

        db.close()
    except Exception:
        # Graceful degradation - continue even if delegation tracking fails
        pass

    # Track Task invocation as activity (if parent session exists)
    task_activity_id = None
    if parent_session:
        try:
            from htmlgraph import SDK

            sdk = SDK(agent=parent_agent, parent_session=parent_session)

            # Track Task invocation
            entry = sdk.track_activity(
                tool="Task",
                summary=f"Task invoked: {tool_params.get('description', 'Unnamed task')[:100]}",
                payload={
                    "subagent_type": tool_params.get("subagent_type"),
                    "description": tool_params.get("description"),
                    "prompt_preview": prompt[:200] if prompt else "",
                    "nesting_depth": nesting_depth,
                },
                success=True,
            )

            if entry:
                task_activity_id = entry.id

        except Exception:
            # Graceful degradation - continue even if tracking fails
            pass

    # Increment nesting depth for child
    new_depth = nesting_depth + 1

    # Set parent activity and increment depth in environment
    if task_activity_id:
        os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = task_activity_id

    os.environ["HTMLGRAPH_NESTING_DEPTH"] = str(new_depth)

    # Warn about runaway recursion
    warning = ""
    if new_depth > 3:
        warning = f"\n⚠️  Warning: Nesting depth exceeds 3 levels (depth={new_depth}). Consider flattening task hierarchy."

    # Check if save instructions already present
    if has_save_instructions(prompt):
        # Even if save instructions exist, we still need to update environment
        return {"continue": True}

    # Detect subagent type from prompt context
    prompt_lower = prompt.lower()
    if "haiku" in prompt_lower:
        subagent_type = "haiku"
    elif "sonnet" in prompt_lower:
        subagent_type = "sonnet"
    elif "opus" in prompt_lower:
        subagent_type = "opus"
    else:
        subagent_type = "haiku"  # Default to haiku for most subagents

    # Inject save instructions
    modified_prompt = inject_save_instructions(prompt, subagent_type)

    # Create updated tool params
    updated_params = tool_params.copy()
    updated_params["prompt"] = modified_prompt

    # Build context message
    context_msg = (
        f"📝 Auto-injected HtmlGraph save instructions into Task prompt. "
        f"Subagent will be reminded to save findings using SDK.spikes. "
        f"(depth={new_depth}, parent={parent_session[:12] if parent_session else 'none'})"
    )
    if warning:
        context_msg += warning

    # Return response with updatedInput
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": updated_params,
            "additionalContext": context_msg,
        },
    }
