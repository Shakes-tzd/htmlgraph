#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
UserPromptSubmit Hook - Analyze prompts and guide workflow.

This hook fires when the user submits a prompt. It analyzes the intent
and provides guidance to ensure proper HtmlGraph workflow:

1. Implementation requests → Ensure work item exists
2. Bug reports → Guide to create bug first
3. Investigation requests → Guide to create spike first
4. Continue/resume → Check for existing work context

Hook Input (stdin): JSON with prompt details
Hook Output (stdout): JSON with guidance (additionalContext)
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


def main():
    """Main entry point."""
    try:
        # Read prompt input from stdin
        hook_input = json.load(sys.stdin)
        prompt = hook_input.get("prompt", "")

        if not prompt:
            # No prompt - no guidance
            print(json.dumps({}))
            sys.exit(0)

        # Classify the prompt
        classification = classify_prompt(prompt)

        # Get active work item
        active_work = get_active_work_item()

        # Generate guidance
        guidance = generate_guidance(classification, active_work, prompt)

        if guidance:
            # Return guidance as additionalContext
            result = {
                "additionalContext": guidance,
                "classification": {
                    "implementation": classification["is_implementation"],
                    "investigation": classification["is_investigation"],
                    "bug_report": classification["is_bug_report"],
                    "continuation": classification["is_continuation"],
                    "confidence": classification["confidence"],
                },
            }
            print(json.dumps(result))
        else:
            print(json.dumps({}))

        # Always allow - this hook provides guidance, not blocking
        sys.exit(0)

    except Exception as e:
        # Graceful degradation
        print(json.dumps({"error": str(e)}))
        sys.exit(0)


if __name__ == "__main__":
    main()
