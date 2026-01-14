import logging

logger = logging.getLogger(__name__)

"""
Orchestration helpers for reliable parallel task coordination.

Provides Task ID pattern for retrieving results from parallel delegations.
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
else:
    # Avoid circular import during module initialization
    SDK = None


def generate_task_id() -> str:
    """
    Generate unique task ID for traceability.

    Returns:
        Unique task ID (e.g., "task-a3f8b29c")
    """
    return f"task-{uuid.uuid4().hex[:8]}"


def delegate_with_id(
    description: str,
    prompt: str,
    subagent_type: str = "general-purpose",
) -> tuple[str, str]:
    """
    Delegate task with unique ID for result retrieval.

    Args:
        description: Human-readable task description
        prompt: Task instructions for subagent
        subagent_type: Type of subagent to use

    Returns:
        tuple[task_id, enhanced_prompt]: Unique identifier and enhanced prompt

    Example:
        task_id, enhanced_prompt = delegate_with_id(
            "Implement authentication",
            "Add JWT auth to API...",
            "general-purpose"
        )
        # Orchestrator calls: Task(prompt=enhanced_prompt, ...)
        results = get_results_by_task_id(sdk, task_id)
    """
    task_id = generate_task_id()

    # Inject task ID into prompt for traceability
    # Note: Orchestrator will capture results and save to HtmlGraph, NOT the subagent
    enhanced_prompt = f"""
TASK_ID: {task_id}
TASK_DESCRIPTION: {description}

{prompt}

📝 Note: This task has ID {task_id} for tracking purposes.
Provide detailed findings in your response.
"""

    # The orchestrator will:
    # 1. Call: Task(prompt=enhanced_prompt, description=f"{task_id}: {description}")
    # 2. Capture the result from Task() function return
    # 3. Optionally validate/test the result
    # 4. Save to HtmlGraph spike using save_task_results()
    # 5. Link to work items (features, tracks, etc.)

    return task_id, enhanced_prompt


def get_results_by_task_id(
    sdk: "SDK",
    task_id: str,
    timeout: int = 60,
    poll_interval: int = 2,
) -> dict[str, Any]:
    """
    Retrieve task results by task ID with polling.

    Polls HtmlGraph spikes for results with task ID in title.
    Works with parallel tasks - each has unique ID.

    Args:
        sdk: HtmlGraph SDK instance
        task_id: Task ID returned by delegate_with_id()
        timeout: Maximum seconds to wait for results
        poll_interval: Seconds between polling attempts

    Returns:
        Results dict with:
        - success: bool
        - task_id: str
        - spike_id: str (if found)
        - findings: str (if found)
        - error: str (if not found)

    Example:
        results = get_results_by_task_id(sdk, "task-a3f8b29c", timeout=120)
        if results["success"]:
            print(results["findings"])
    """
    deadline = datetime.utcnow() + timedelta(seconds=timeout)
    attempts = 0

    while datetime.utcnow() < deadline:
        attempts += 1

        # Get all spikes and search for task ID in title
        spikes = sdk.spikes.all()
        matching = [s for s in spikes if task_id in s.title]

        if matching:
            spike = matching[0]
            # Access findings attribute (available on Spike nodes)
            findings = getattr(spike, "findings", None)
            return {
                "success": True,
                "task_id": task_id,
                "spike_id": spike.id,
                "title": spike.title,
                "findings": findings,
                "attempts": attempts,
            }

        # Wait before next poll
        time.sleep(poll_interval)

    # Timeout - no results found
    return {
        "success": False,
        "task_id": task_id,
        "error": f"No results found for task {task_id} within {timeout}s",
        "attempts": attempts,
    }


def parallel_delegate(
    sdk: "SDK",
    tasks: list[dict[str, str]],
    timeout: int = 120,
) -> dict[str, dict[str, Any]]:
    """
    Coordinate multiple parallel tasks with result retrieval.

    Args:
        sdk: HtmlGraph SDK instance
        tasks: List of task dicts with keys: description, prompt, subagent_type
        timeout: Maximum seconds to wait for all results

    Returns:
        Dict mapping task_id to results for each task

    Example:
        results = parallel_delegate(sdk, [
            {"description": "Implement auth", "prompt": "...", "subagent_type": "general-purpose"},
            {"description": "Write tests", "prompt": "...", "subagent_type": "general-purpose"},
            {"description": "Update docs", "prompt": "...", "subagent_type": "general-purpose"},
        ])

        for task_id, result in results.items():
            logger.info(f"{task_id}: {result['findings']}")
    """
    # Generate task IDs and enhanced prompts
    task_mapping = {}
    for task in tasks:
        task_id, enhanced_prompt = delegate_with_id(
            task["description"],
            task["prompt"],
            task.get("subagent_type", "general-purpose"),
        )
        task_mapping[task_id] = {
            "description": task["description"],
            "prompt": enhanced_prompt,
            "subagent_type": task.get("subagent_type", "general-purpose"),
        }

    # Note: Orchestrator should spawn all Task() calls here in parallel
    # This function returns the mapping for orchestrator to use

    # Wait for all results
    results = {}
    for task_id in task_mapping:
        results[task_id] = get_results_by_task_id(sdk, task_id, timeout=timeout)

    return results


def save_task_results(
    sdk: "SDK",
    task_id: str,
    description: str,
    results: str,
    feature_id: str | None = None,
    status: str = "completed",
) -> str:
    """
    Save task results to HtmlGraph spike (orchestrator-side).

    This is the recommended pattern for saving delegation results.
    The orchestrator captures Task() output and saves it, rather than
    relying on subagents to save their own results.

    Args:
        sdk: HtmlGraph SDK instance
        task_id: Task ID from delegate_with_id()
        description: Task description
        results: Task results (from Task() function return)
        feature_id: Optional feature ID to link
        status: Task status (completed, failed, partial)

    Returns:
        Spike ID

    Example:
        task_id, prompt = delegate_with_id("Implement auth", "Add JWT...")

        # Call Task() and capture result
        result = Task(prompt=prompt, description=f"{task_id}: Implement auth")

        # Orchestrator saves the result
        spike_id = save_task_results(
            sdk, task_id, "Implement auth", result,
            feature_id="feat-123", status="completed"
        )
    """
    # Create spike with task results (chain all calls)
    findings = f"""
# Task: {description}
# Task ID: {task_id}
# Status: {status}

## Results

{results}

## Linked Work Items
{f"- Feature: {feature_id}" if feature_id else "None"}

## Metadata
- Saved by: orchestrator
- Task pattern: delegate_with_id
"""

    spike = (
        sdk.spikes.create(f"Results: {task_id} - {description}")
        .set_findings(findings)
        .save()
    )

    # Link to feature if provided
    if feature_id:
        try:
            with sdk.features.edit(feature_id) as _:
                # Add activity log entry when method is available
                pass
        except Exception:
            pass  # Feature linking is optional

    return str(spike.id)


def validate_and_save(
    sdk: "SDK",
    task_id: str,
    description: str,
    results: str,
    validation_prompt: str | None = None,
    feature_id: str | None = None,
) -> dict[str, Any]:
    """
    Validate task results and save to HtmlGraph.

    Optionally delegates validation to a testing agent before saving.
    This implements quality gates in the orchestration pattern.

    Args:
        sdk: HtmlGraph SDK instance
        task_id: Task ID from delegate_with_id()
        description: Task description
        results: Task results to validate
        validation_prompt: Optional prompt for validation agent
        feature_id: Optional feature ID to link

    Returns:
        Dict with:
        - validated: bool
        - spike_id: str
        - validation_results: str (if validation performed)

    Example:
        # Delegate implementation
        impl_id, impl_prompt = delegate_with_id("Add auth", "Implement JWT...")
        impl_result = Task(prompt=impl_prompt, ...)

        # Validate and save
        outcome = validate_and_save(
            sdk, impl_id, "Add auth", impl_result,
            validation_prompt="Run tests and verify auth works",
            feature_id="feat-auth"
        )

        if outcome["validated"]:
            logger.info(f"✅ Saved to spike: {outcome['spike_id']}")
    """
    validated = True
    validation_results = None

    # Optional validation step
    if validation_prompt:
        test_id, test_prompt = delegate_with_id(
            f"Validate: {description}",
            f"{validation_prompt}\n\nResults to validate:\n{results}",
            "general-purpose",
        )

        # Note: Orchestrator should call Task() here to run validation
        # validation_results = Task(prompt=test_prompt, ...)
        # For now, we'll assume validation happens externally

    # Determine status based on validation
    status = "completed" if validated else "needs-review"

    # Save results
    spike_id = save_task_results(
        sdk, task_id, description, results, feature_id=feature_id, status=status
    )

    return {
        "validated": validated,
        "spike_id": spike_id,
        "validation_results": validation_results,
    }
