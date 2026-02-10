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

1. Implementation requests -> Ensure work item exists + CIGS imperative guidance
2. Bug reports -> Guide to create bug first
3. Investigation requests -> Guide to create spike first
4. Continue/resume -> Check for existing work context
5. CIGS integration -> Pre-response delegation reminders based on intent

Hook Input (stdin): JSON with prompt details
Hook Output (stdout): JSON with guidance (additionalContext)

Thin wrapper around SDK prompt_analyzer module. All business logic lives in:
    htmlgraph.hooks.prompt_analyzer
"""

import json
import os
import sys

# Bootstrap Python path and setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bootstrap import bootstrap_pythonpath, resolve_project_dir

project_dir_for_import = resolve_project_dir()
bootstrap_pythonpath(project_dir_for_import)

# Import all business logic from SDK prompt_analyzer
from htmlgraph.hooks.context import HookContext
from htmlgraph.hooks.prompt_analyzer import (
    classify_cigs_intent,
    classify_prompt,
    generate_cigs_guidance,
    generate_guidance,
    get_active_work_item,
    get_session_violation_count,
)


def main() -> None:
    """Main entry point with CIGS integration."""
    try:
        # Read prompt input from stdin
        hook_input = json.load(sys.stdin)
        prompt = hook_input.get("prompt", "")

        if not prompt:
            # No prompt - no guidance
            print(json.dumps({}))
            sys.exit(0)

        # Build HookContext for SDK functions that require it
        context = HookContext.from_input(hook_input)

        # 1. Classify the prompt (SDK)
        classification = classify_prompt(prompt)

        # 2. CIGS: Classify for delegation guidance (SDK)
        cigs_intent = classify_cigs_intent(prompt)

        # 3. CIGS: Get violation count (SDK)
        violation_count, waste_tokens = get_session_violation_count(context)

        # 4. Get active work item (SDK)
        active_work = get_active_work_item(context)

        # 5. Generate workflow guidance (SDK)
        workflow_guidance = generate_guidance(classification, active_work, prompt)

        # 6. CIGS: Generate imperative delegation guidance (SDK)
        cigs_guidance = generate_cigs_guidance(
            cigs_intent, violation_count, waste_tokens
        )

        # 7. Combine both guidance types
        combined_guidance = []

        if cigs_guidance:
            combined_guidance.append(cigs_guidance)

        if workflow_guidance:
            combined_guidance.append(workflow_guidance)

        # CRITICAL FIX: Record UserQuery event BEFORE printing output
        # This ensures the query is tracked for dashboard display
        try:
            from bootstrap import get_graph_dir, resolve_project_dir

            project_dir = resolve_project_dir()
            get_graph_dir(project_dir)

            # Use session_id from hook_input if available
            session_id = hook_input.get("session_id") or hook_input.get("sessionId")

            if session_id and prompt:
                # Strip subagent suffixes to ensure UserQuery is in parent session
                # Known suffixes: -general-purpose, -Explore, -Bash, -Plan, -researcher, -debugger, etc.
                known_suffixes = [
                    "-general-purpose",
                    "-Explore",
                    "-Bash",
                    "-Plan",
                    "-researcher",
                    "-debugger",
                    "-test-runner",
                    "-codex-spawner",
                    "-gemini-spawner",
                ]
                parent_session_id = session_id  # Default: same session
                for suffix in known_suffixes:
                    if session_id.endswith(suffix):
                        parent_session_id = session_id[: -len(suffix)]
                        print(
                            f"[UserQuery] Stripped suffix '{suffix}' from session_id: {session_id} -> {parent_session_id}",
                            file=sys.stderr,
                        )
                        break

                # CRITICAL: Use direct SQLite INSERT to avoid SessionNotFoundError
                # The parent session may not exist yet (subagents launched before parent session file created)
                from htmlgraph.config import get_database_path
                from htmlgraph.database import HtmlGraphDB
                from htmlgraph.hooks.event_tracker import record_event

                db_path = str(get_database_path())
                db = HtmlGraphDB(db_path)

                # Ensure session exists (create placeholder if needed) - same pattern as PreToolUse
                db._ensure_session_exists(parent_session_id, "system")

                # Record UserQuery event directly to database
                prompt_preview = prompt[:100].replace("\n", " ")
                if len(prompt) > 100:
                    prompt_preview += "..."

                record_event(
                    db=db,
                    session_id=parent_session_id,
                    tool_name="UserQuery",
                    summary=f'"{prompt_preview}"',
                    status="completed",
                    tool_input={"prompt": prompt},
                    parent_event_id=None,  # UserQuery is always a root event
                )

                print(
                    f"[UserQuery] Created event in session {parent_session_id}",
                    file=sys.stderr,
                )
        except Exception as e:
            # Don't break the hook if tracking fails
            import traceback

            print(f"Warning: Failed to track UserQuery event: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        # Now print the JSON output for Claude Code
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
