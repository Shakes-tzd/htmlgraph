#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
UserPromptSubmit Hook - Analyze prompts and guide workflow with CIGS integration.

This hook fires when the user submits a prompt. It analyzes the intent
and provides guidance to ensure proper HtmlGraph workflow:

1. Implementation requests → Ensure work item exists + CIGS imperative guidance
2. Bug reports → Guide to create bug first
3. Investigation requests → Guide to create spike first
4. Continue/resume → Check for existing work context
5. CIGS integration → Pre-response delegation reminders based on intent

Hook Input (stdin): JSON with prompt details
Hook Output (stdout): JSON with guidance (additionalContext)

CIGS Integration:
- Detects prompt intent (exploration, code changes, git)
- Loads session violation count
- Generates pre-response imperative guidance
- Includes violation warnings if violations > 0
"""

import json
import re
import sys

# Patterns that indicate implementation intent
IMPLEMENTATION_PATTERNS = [
    r"\b(implement|add|create|build|write|develop|make)\b.*\b(feature|function|method|class|component|endpoint|api)\b",
    r"\b(fix|resolve|patch|repair)\b.*\b(bug|issue|error|problem)\b",
    r"\b(refactor|rewrite|restructure|reorganize)\b",
    r"\b(update|modify|change|edit)\b.*\b(code|file|function|class)\b",
    r"\bcan you\b.*\b(add|implement|create|fix|change)\b",
    r"\bplease\b.*\b(add|implement|create|fix|change)\b",
    r"\bI need\b.*\b(feature|function|fix|change)\b",
    r"\blet'?s\b.*\b(implement|add|create|build|fix)\b",
]

# Patterns that indicate investigation/research
INVESTIGATION_PATTERNS = [
    r"\b(investigate|research|explore|analyze|understand|find out|look into)\b",
    r"\b(why|how come|what causes)\b.*\b(not working|broken|failing|error)\b",
    r"\b(where|which|what)\b.*\b(file|code|function|class)\b.*\b(handle|process|do)\b",
    r"\bcan you\b.*\b(find|search|look for|check)\b",
]

# Patterns that indicate bug/issue
BUG_PATTERNS = [
    r"\b(bug|issue|error|problem|broken|not working|fails|crash)\b",
    r"\b(something'?s? wrong|doesn'?t work|isn'?t working)\b",
    r"\bCI\b.*\b(fail|error|broken)\b",
    r"\btest.*\b(fail|error|broken)\b",
]

# Patterns for continuation
CONTINUATION_PATTERNS = [
    r"^(continue|resume|proceed|go on|keep going|next)\b",
    r"\b(where we left off|from before|last time)\b",
    r"^(ok|okay|yes|sure|do it|go ahead)\b",
]

# CIGS: Patterns for delegation-critical operations
EXPLORATION_KEYWORDS = [
    "search",
    "find",
    "what files",
    "which files",
    "where is",
    "locate",
    "analyze",
    "examine",
    "inspect",
    "review",
    "check",
    "look at",
    "show me",
    "list",
    "grep",
    "read",
    "scan",
    "explore",
]

CODE_CHANGE_KEYWORDS = [
    "implement",
    "fix",
    "update",
    "refactor",
    "change",
    "modify",
    "edit",
    "write",
    "create file",
    "add code",
    "remove code",
    "replace",
    "rewrite",
    "patch",
    "add",
]

GIT_KEYWORDS = [
    "commit",
    "push",
    "pull",
    "merge",
    "branch",
    "checkout",
    "git add",
    "git commit",
    "git push",
    "git status",
    "git diff",
    "rebase",
    "cherry-pick",
    "stash",
]


def classify_prompt(prompt: str) -> dict:
    """Classify the user's prompt intent."""
    prompt_lower = prompt.lower().strip()

    result = {
        "is_implementation": False,
        "is_investigation": False,
        "is_bug_report": False,
        "is_continuation": False,
        "confidence": 0.0,
        "matched_patterns": [],
    }

    # Check for continuation first (short prompts like "ok", "continue")
    for pattern in CONTINUATION_PATTERNS:
        if re.search(pattern, prompt_lower):
            result["is_continuation"] = True
            result["confidence"] = 0.9
            result["matched_patterns"].append(f"continuation: {pattern}")
            return result

    # Check for implementation patterns
    for pattern in IMPLEMENTATION_PATTERNS:
        if re.search(pattern, prompt_lower):
            result["is_implementation"] = True
            result["confidence"] = max(result["confidence"], 0.8)
            result["matched_patterns"].append(f"implementation: {pattern}")

    # Check for investigation patterns
    for pattern in INVESTIGATION_PATTERNS:
        if re.search(pattern, prompt_lower):
            result["is_investigation"] = True
            result["confidence"] = max(result["confidence"], 0.7)
            result["matched_patterns"].append(f"investigation: {pattern}")

    # Check for bug patterns
    for pattern in BUG_PATTERNS:
        if re.search(pattern, prompt_lower):
            result["is_bug_report"] = True
            result["confidence"] = max(result["confidence"], 0.75)
            result["matched_patterns"].append(f"bug: {pattern}")

    return result


def classify_cigs_intent(prompt: str) -> dict:
    """Classify prompt for CIGS delegation guidance.

    Returns:
        dict with:
            - involves_exploration: bool
            - involves_code_changes: bool
            - involves_git: bool
            - intent_confidence: float (0.0-1.0)
    """
    prompt_lower = prompt.lower().strip()

    result = {
        "involves_exploration": False,
        "involves_code_changes": False,
        "involves_git": False,
        "intent_confidence": 0.0,
    }

    # Check for exploration keywords
    exploration_matches = sum(1 for kw in EXPLORATION_KEYWORDS if kw in prompt_lower)
    if exploration_matches > 0:
        result["involves_exploration"] = True
        result["intent_confidence"] = min(1.0, exploration_matches * 0.3)

    # Check for code change keywords
    code_matches = sum(1 for kw in CODE_CHANGE_KEYWORDS if kw in prompt_lower)
    if code_matches > 0:
        result["involves_code_changes"] = True
        result["intent_confidence"] = max(
            result["intent_confidence"], min(1.0, code_matches * 0.35)
        )

    # Check for git keywords
    git_matches = sum(1 for kw in GIT_KEYWORDS if kw in prompt_lower)
    if git_matches > 0:
        result["involves_git"] = True
        result["intent_confidence"] = max(
            result["intent_confidence"], min(1.0, git_matches * 0.4)
        )

    return result


def get_session_violation_count() -> tuple[int, int]:
    """Get violation count for current session using CIGS ViolationTracker.

    Returns:
        Tuple of (violation_count, total_waste_tokens)
    """
    try:
        from htmlgraph.cigs import ViolationTracker

        tracker = ViolationTracker()
        summary = tracker.get_session_violations()
        return summary.total_violations, summary.total_waste_tokens
    except Exception:
        # Graceful degradation if CIGS not available
        return 0, 0


def generate_cigs_guidance(
    cigs_intent: dict, violation_count: int, waste_tokens: int
) -> str:
    """Generate pre-response CIGS imperative guidance.

    Args:
        cigs_intent: Intent classification from classify_cigs_intent()
        violation_count: Number of violations this session
        waste_tokens: Total wasted tokens this session

    Returns:
        Imperative guidance string (empty if no guidance needed)
    """
    imperatives = []

    # Exploration guidance
    if cigs_intent["involves_exploration"]:
        imperatives.append(
            "🔴 IMPERATIVE: This request involves exploration.\n"
            "YOU MUST use spawn_gemini() for exploration (FREE cost).\n"
            "DO NOT use Read/Grep/Glob directly - delegate to Explorer subagent."
        )

    # Code changes guidance
    if cigs_intent["involves_code_changes"]:
        imperatives.append(
            "🔴 IMPERATIVE: This request involves code changes.\n"
            "YOU MUST use spawn_codex() or Task() for implementation.\n"
            "DO NOT use Edit/Write directly - delegate to Coder subagent."
        )

    # Git operations guidance
    if cigs_intent["involves_git"]:
        imperatives.append(
            "🔴 IMPERATIVE: This request involves git operations.\n"
            "YOU MUST use spawn_copilot() for git commands (60% cheaper).\n"
            "DO NOT run git commands directly via Bash."
        )

    # Violation warning
    if violation_count > 0:
        warning_emoji = "⚠️" if violation_count < 3 else "🚨"
        imperatives.append(
            f"{warning_emoji} VIOLATION WARNING: You have {violation_count} delegation "
            f"violations this session ({waste_tokens:,} tokens wasted).\n"
            f"Circuit breaker triggers at 3 violations."
        )

    if not imperatives:
        return ""

    # Combine with header
    guidance_parts = [
        "═══════════════════════════════════════════════════════════",
        "CIGS PRE-RESPONSE GUIDANCE (Computational Imperative Guidance System)",
        "═══════════════════════════════════════════════════════════",
        "",
    ]
    guidance_parts.extend(imperatives)
    guidance_parts.append("")
    guidance_parts.append("═══════════════════════════════════════════════════════════")

    return "\n".join(guidance_parts)


def get_active_work_item() -> dict | None:
    """Get active work item using SDK."""
    try:
        from htmlgraph import SDK

        sdk = SDK()
        return sdk.get_active_work_item()
    except Exception:
        return None


def generate_guidance(
    classification: dict, active_work: dict | None, prompt: str
) -> str | None:
    """Generate workflow guidance based on classification and context."""

    # If continuing and has active work, no guidance needed
    if classification["is_continuation"] and active_work:
        return None

    # If has active work item, check if it matches intent
    if active_work:
        work_type = active_work.get("type", "")
        work_id = active_work.get("id", "")
        work_title = active_work.get("title", "")

        # Implementation request with spike active - suggest creating feature
        if classification["is_implementation"] and work_type == "spike":
            return (
                f"⚡ ORCHESTRATOR DIRECTIVE: Implementation requested during spike.\n\n"
                f"Active work: {work_id} ({work_title}) - Type: spike\n\n"
                f"Spikes are for investigation, NOT implementation.\n\n"
                f"REQUIRED WORKFLOW:\n\n"
                f"1. COMPLETE OR PAUSE the spike:\n"
                f"   sdk = SDK(agent='claude')\n"
                f"   sdk.spikes.complete('{work_id}')  # or sdk.spikes.pause('{work_id}')\n\n"
                f"2. CREATE A FEATURE for implementation:\n"
                f"   feature = sdk.features.create('Feature title').save()\n"
                f"   sdk.features.start(feature.id)\n\n"
                f"3. DELEGATE TO SUBAGENT:\n"
                f"   from htmlgraph.tasks import Task\n"
                f"   Task(\n"
                f"       subagent_type='general-purpose',\n"
                f"       prompt='Implement: [details]'\n"
                f"   ).execute()\n\n"
                f"Proceed with orchestration.\n"
            )

        # Implementation request with feature active - remind to delegate
        if classification["is_implementation"] and work_type == "feature":
            return (
                f"⚡ ORCHESTRATOR DIRECTIVE: Implementation work detected.\n\n"
                f"Active work: {work_id} ({work_title}) - Type: feature\n\n"
                f"REQUIRED: DELEGATE TO SUBAGENT:\n\n"
                f"  from htmlgraph.tasks import Task\n"
                f"  Task(\n"
                f"      subagent_type='general-purpose',\n"
                f"      prompt='Implement: [specific implementation details for {work_title}]'\n"
                f"  ).execute()\n\n"
                f"DO NOT EXECUTE CODE DIRECTLY IN THIS CONTEXT.\n"
                f"Orchestrators coordinate, subagents implement.\n\n"
                f"Proceed with orchestration.\n"
            )

        # Bug report with feature active - might want bug instead
        if classification["is_bug_report"] and work_type == "feature":
            return (
                f"📋 WORKFLOW GUIDANCE:\n"
                f"Active work: {work_id} ({work_title}) - Type: feature\n\n"
                f"This looks like a bug report. Consider:\n"
                f"1. If this bug is part of {work_title}, continue with current feature\n"
                f"2. If this is a separate issue, create a bug:\n\n"
                f"  sdk = SDK(agent='claude')\n"
                f"  bug = sdk.bugs.create('Bug title').save()\n"
                f"  sdk.bugs.start(bug.id)\n"
            )

        # Has appropriate work item - no guidance needed
        return None

    # No active work item - provide guidance based on intent
    if classification["is_implementation"]:
        return (
            "⚡ ORCHESTRATOR DIRECTIVE: This is implementation work.\n\n"
            "REQUIRED WORKFLOW (execute in order):\n\n"
            "1. CREATE A WORK ITEM:\n"
            "   sdk = SDK(agent='claude')\n"
            "   feature = sdk.features.create('Your feature title').save()\n"
            "   sdk.features.start(feature.id)\n\n"
            "2. DELEGATE TO SUBAGENT:\n"
            "   from htmlgraph.tasks import Task\n"
            "   Task(\n"
            "       subagent_type='general-purpose',\n"
            "       prompt='Implement: [specific implementation details]'\n"
            "   ).execute()\n\n"
            "3. DO NOT EXECUTE CODE DIRECTLY IN THIS CONTEXT\n"
            "   - Orchestrators coordinate, subagents implement\n"
            "   - This ensures proper work tracking and session management\n\n"
            "Proceed with orchestration.\n"
        )

    if classification["is_bug_report"]:
        return (
            "📋 WORKFLOW GUIDANCE - BUG REPORT DETECTED:\n\n"
            "Create a bug work item to track this:\n\n"
            "  sdk = SDK(agent='claude')\n"
            "  bug = sdk.bugs.create('Bug title').save()\n"
            "  sdk.bugs.start(bug.id)\n\n"
            "Then investigate and fix the issue.\n"
        )

    if classification["is_investigation"]:
        return (
            "📋 WORKFLOW GUIDANCE - INVESTIGATION REQUEST DETECTED:\n\n"
            "Create a spike for time-boxed investigation:\n\n"
            "  sdk = SDK(agent='claude')\n"
            "  spike = sdk.spikes.create('Investigation title').save()\n"
            "  sdk.spikes.start(spike.id)\n\n"
            "Spikes help track research and exploration work.\n"
        )

    # Low confidence or unclear intent - provide gentle reminder
    if classification["confidence"] < 0.5:
        return (
            "💡 REMINDER: Consider creating a work item if this is a task:\n"
            "- Feature: sdk.features.create('Title').save()\n"
            "- Bug: sdk.bugs.create('Title').save()\n"
            "- Spike: sdk.spikes.create('Title').save()\n"
        )

    return None


def create_user_query_event(prompt: str) -> str | None:
    """
    Create a UserQuery event in the HtmlGraph database.

    This ensures that user prompts are recorded as events that can serve as
    parent events for subsequent tool calls and delegations. The event ID is
    saved to a session-scoped file for later retrieval by PreToolUse hook.

    Args:
        prompt: User's prompt text

    Returns:
        UserQuery event_id if successful, None otherwise
    """
    try:
        import uuid
        import os
        from pathlib import Path
        from datetime import datetime, timezone

        # Get session ID from environment
        session_id = os.environ.get("HTMLGRAPH_SESSION_ID")
        if not session_id:
            # Fallback: Try to load from .htmlgraph/sessions
            try:
                cwd = os.getcwd()
                graph_dir = Path(cwd) / ".htmlgraph"
                sessions_dir = graph_dir / "sessions"

                if sessions_dir.exists():
                    import re
                    session_files = sorted(
                        sessions_dir.glob("sess-*.html"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )

                    for session_file in session_files:
                        match = re.search(r"sess-([a-f0-9]+)", session_file.name)
                        if match:
                            session_id = f"sess-{match.group(1)}"
                            break
            except Exception:
                pass

        if not session_id:
            return None

        # Create UserQuery event in database
        try:
            from htmlgraph.db.schema import HtmlGraphDB
            from htmlgraph.hooks.event_tracker import save_user_query_event

            db = HtmlGraphDB()

            # Generate event ID
            user_query_event_id = f"uq-{uuid.uuid4().hex[:8]}"

            # Prepare event details
            input_summary = prompt[:200]

            # Insert UserQuery event into agent_events
            success = db.insert_event(
                event_id=user_query_event_id,
                agent_id="user",
                event_type="tool_call",  # UserQuery appears as a tool_call event
                session_id=session_id,
                tool_name="UserQuery",
                input_summary=input_summary,
                context={
                    "prompt": prompt[:500],
                    "session": session_id,
                }
            )

            if not success:
                return None

            # Save event ID to session-scoped file for subsequent tool calls
            # This is used by PreToolUse hook to link Task delegations
            try:
                cwd = os.getcwd()
                graph_dir = Path(cwd) / ".htmlgraph"
                save_user_query_event(graph_dir, session_id, user_query_event_id)
            except Exception:
                # If saving to file fails, still continue (database insert succeeded)
                pass

            return user_query_event_id

        except Exception:
            # Database tracking is optional - graceful degradation
            return None

    except Exception:
        # Silent failure - don't block user interaction
        return None


def main():
    """Main entry point with CIGS integration."""
    try:
        # Read prompt input from stdin
        hook_input = json.load(sys.stdin)
        prompt = hook_input.get("prompt", "")

        if not prompt:
            # No prompt - no guidance
            print(json.dumps({}))
            sys.exit(0)

        # 0. Create UserQuery event in database for parent-child linking
        user_query_event_id = create_user_query_event(prompt)

        # 1. Classify the prompt (existing workflow guidance)
        classification = classify_prompt(prompt)

        # 2. CIGS: Classify for delegation guidance
        cigs_intent = classify_cigs_intent(prompt)

        # 3. CIGS: Get violation count
        violation_count, waste_tokens = get_session_violation_count()

        # 4. Get active work item
        active_work = get_active_work_item()

        # 5. Generate workflow guidance (existing)
        workflow_guidance = generate_guidance(classification, active_work, prompt)

        # 6. CIGS: Generate imperative delegation guidance
        cigs_guidance = generate_cigs_guidance(
            cigs_intent, violation_count, waste_tokens
        )

        # 7. Combine both guidance types
        combined_guidance = []

        if cigs_guidance:
            combined_guidance.append(cigs_guidance)

        if workflow_guidance:
            combined_guidance.append(workflow_guidance)

        if combined_guidance:
            # Return combined guidance as additionalContext
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "\n\n".join(combined_guidance),
                },
                "classification": {
                    "implementation": classification["is_implementation"],
                    "investigation": classification["is_investigation"],
                    "bug_report": classification["is_bug_report"],
                    "continuation": classification["is_continuation"],
                    "confidence": classification["confidence"],
                },
                "cigs_classification": {
                    "involves_exploration": cigs_intent["involves_exploration"],
                    "involves_code_changes": cigs_intent["involves_code_changes"],
                    "involves_git": cigs_intent["involves_git"],
                    "intent_confidence": cigs_intent["intent_confidence"],
                },
                "cigs_session_status": {
                    "violation_count": violation_count,
                    "waste_tokens": waste_tokens,
                },
                "user_query_event": {
                    "event_id": user_query_event_id,
                },
            }
            print(json.dumps(result))
        else:
            print(json.dumps({}))

        # Always allow - this hook provides guidance, not blocking
        sys.exit(0)

    except Exception as e:
        # Graceful degradation
        import traceback

        error_detail = traceback.format_exc()
        print(json.dumps({"error": str(e), "traceback": error_detail}), file=sys.stderr)
        # Still return empty result to not block
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
