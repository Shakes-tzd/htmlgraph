#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
UserPromptSubmit Hook - Thin shell for prompt analysis and workflow guidance.

Delegates all logic to htmlgraph.hooks.prompt_analyzer and htmlgraph.hooks.context.
This script is now a 20-30 line wrapper that orchestrates:
1. Prompt classification (implementation, investigation, bug, continuation)
2. CIGS intent detection (exploration, code changes, git operations)
3. Workflow guidance generation
4. UserQuery event creation for parent-child linking
"""

import json
import sys

from htmlgraph.hooks.bootstrap import init_logger
from htmlgraph.hooks.context import HookContext
from htmlgraph.hooks.prompt_analyzer import (
    classify_cigs_intent,
    classify_prompt,
    create_user_query_event,
    generate_cigs_guidance,
    generate_guidance,
    get_active_work_item,
    get_session_violation_count,
)

logger = init_logger(__name__)


def main():
    """Main entry point - orchestrates prompt analysis and guidance."""
    try:
        # Load hook input from stdin
        hook_input = json.load(sys.stdin)
        prompt = hook_input.get("prompt", "")

        if not prompt:
            print(json.dumps({}))
            sys.exit(0)

        # Create execution context
        context = HookContext.from_input(hook_input)

        try:
            # Run all analysis in parallel
            classification = classify_prompt(prompt)
            cigs_intent = classify_cigs_intent(prompt)
            violation_count, waste_tokens = get_session_violation_count(context)
            active_work = get_active_work_item(context)
            user_query_event_id = create_user_query_event(context, prompt)

            # Generate guidance
            workflow_guidance = generate_guidance(classification, active_work, prompt)
            cigs_guidance = generate_cigs_guidance(
                cigs_intent, violation_count, waste_tokens
            )

            # Combine guidance
            combined_guidance = [g for g in [cigs_guidance, workflow_guidance] if g]

            if combined_guidance:
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
                    "user_query_event": {"event_id": user_query_event_id},
                }
                print(json.dumps(result))
            else:
                print(json.dumps({}))

        finally:
            context.close()

        sys.exit(0)

    except Exception as e:
        logger.error(f"Hook failed: {e}", exc_info=True)
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
