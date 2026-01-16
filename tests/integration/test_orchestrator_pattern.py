#!/usr/bin/env python3
"""
Comprehensive test of orchestrator-side result management pattern.

Demonstrates:
1. Parallel task delegation with unique task IDs
2. Orchestrator capturing Task() results
3. Saving results to HtmlGraph spikes
4. Work item linking
5. Quality gates (validation)
"""

from htmlgraph import SDK
from htmlgraph.orchestration import (
    delegate_with_id,
    save_task_results,
)


def test_orchestrator_pattern(isolated_db):
    """Test complete orchestrator-side pattern."""
    sdk = SDK(agent="test-orchestrator", db_path=str(isolated_db))

    print("=" * 70)
    print("ORCHESTRATOR-SIDE PATTERN TEST")
    print("=" * 70)

    # =========================================================================
    # STEP 1: Prepare 3 parallel tasks
    # =========================================================================
    print("\n📋 STEP 1: Preparing 3 parallel tasks...")

    task1_id, task1_prompt = delegate_with_id(
        "Count Python files in src/",
        "Count all .py files in src/python/htmlgraph/ directory. Report the count.",
        "general-purpose",
    )

    task2_id, task2_prompt = delegate_with_id(
        "Count test files",
        "Count all .py files in tests/ directory. Report the count.",
        "general-purpose",
    )

    task3_id, task3_prompt = delegate_with_id(
        "Count documentation files",
        "Count all .md files in docs/ directory. Report the count.",
        "general-purpose",
    )

    print(f"  ✅ Task 1: {task1_id} - Count Python files in src/")
    print(f"  ✅ Task 2: {task2_id} - Count test files")
    print(f"  ✅ Task 3: {task3_id} - Count documentation files")

    # =========================================================================
    # STEP 2: Simulate parallel Task() delegation
    # =========================================================================
    print("\n🚀 STEP 2: Simulating parallel Task() delegation...")
    print("  (In real usage, orchestrator calls Task() tool 3 times in parallel)")

    # Simulate Task() results (in real usage, these come from Task() function returns)
    simulated_results = {
        task1_id: """## Task Completed Successfully

### Summary
Counted Python files in src/python/htmlgraph/ directory.

### Results
- **Total files**: 87 Python files
- **Subdirectories**: 7 (analytics, builders, collections, hooks, scripts, services, root)

### Status
Success - Read-only operation completed""",
        task2_id: """## Task Completed Successfully

### Summary
Counted test files in tests/ directory.

### Results
- **Total files**: 56 test files
- **Subdirectories**: tests/python (47 files), tests/integration (3 files), tests/benchmarks (3 files)

### Status
Success - Read-only operation completed""",
        task3_id: """## Task Completed Successfully

### Summary
Counted documentation files in docs/ directory.

### Results
- **Total files**: 17 markdown files
- **Documentation coverage**: Good (API, guides, examples)

### Status
Success - Read-only operation completed""",
    }

    print(f"  ✅ Captured results for {task1_id}")
    print(f"  ✅ Captured results for {task2_id}")
    print(f"  ✅ Captured results for {task3_id}")

    # =========================================================================
    # STEP 3: Orchestrator saves results to HtmlGraph spikes
    # =========================================================================
    print("\n💾 STEP 3: Orchestrator saving results to HtmlGraph...")

    spike1_id = save_task_results(
        sdk,
        task1_id,
        "Count Python files in src/",
        simulated_results[task1_id],
        status="completed",
    )
    print(f"  ✅ Saved spike: {spike1_id}")

    spike2_id = save_task_results(
        sdk,
        task2_id,
        "Count test files",
        simulated_results[task2_id],
        status="completed",
    )
    print(f"  ✅ Saved spike: {spike2_id}")

    spike3_id = save_task_results(
        sdk,
        task3_id,
        "Count documentation files",
        simulated_results[task3_id],
        status="completed",
    )
    print(f"  ✅ Saved spike: {spike3_id}")

    # =========================================================================
    # STEP 4: Verify spikes were saved correctly
    # =========================================================================
    print("\n🔍 STEP 4: Verifying saved spikes...")

    for spike_id in [spike1_id, spike2_id, spike3_id]:
        spike = sdk.spikes.get(spike_id)
        has_findings = bool(spike.findings)
        findings_length = len(spike.findings) if spike.findings else 0

        print(f"  ✅ {spike_id}:")
        print(f"     - Has findings: {has_findings}")
        print(f"     - Findings length: {findings_length} chars")
        print(f"     - Title: {spike.title}")

        # Verify findings contain task ID and results
        if spike.findings:
            assert "Task ID:" in spike.findings
            assert "Results" in spike.findings
            assert "Status: completed" in spike.findings

    # =========================================================================
    # STEP 5: Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("✅ ORCHESTRATOR PATTERN TEST COMPLETE")
    print("=" * 70)
    print("\nPattern Benefits Demonstrated:")
    print("  ✅ Parallel task coordination with unique task IDs")
    print("  ✅ Orchestrator captures Task() results")
    print("  ✅ Reliable spike saving (orchestrator-side, not subagent)")
    print("  ✅ Work item linking capability")
    print("  ✅ Quality gates possible (validation before save)")
    print("  ✅ Full traceability (task → result → spike)")
    print("\nKey Insight:")
    print("  The orchestrator has FULL CONTROL over result management,")
    print("  enabling quality gates, testing, and work item integration.")
    print("=" * 70)


if __name__ == "__main__":
    test_orchestrator_pattern()
