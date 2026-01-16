#!/usr/bin/env python3
"""
Phase 4 Final Test - Generate delegation events for testing.

This script creates test features using the SDK to verify that delegation events
are being recorded in the agent_collaboration table.

Created features:
1. "Phase 4 Final Test Feature 1" - 3 steps, marked in_progress
2. "Phase 4 Final Test Feature 2" - 2 steps, marked in_progress
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src/python"))

from htmlgraph import SDK


def main():
    """Create test features and mark them as in_progress."""

    print("=" * 70)
    print("PHASE 4 FINAL TEST - DELEGATION EVENTS GENERATION")
    print("=" * 70)
    print()

    # Initialize SDK with agent attribution
    sdk = SDK(agent="codex-phase4-final-test")
    print("SDK initialized with agent: codex-phase4-final-test")
    print(f"Working directory: {sdk._graph.root_directory}")
    print()

    # Create Feature 1: 3 steps
    print("-" * 70)
    print("Creating Feature 1: Phase 4 Final Test Feature 1")
    print("-" * 70)

    feature1 = (
        sdk.features.create("Phase 4 Final Test Feature 1")
        .set_priority("high")
        .add_steps(
            [
                "Step 1: Initial setup and validation",
                "Step 2: Core implementation",
                "Step 3: Testing and verification",
            ]
        )
        .save()
    )

    print(f"Feature 1 created: {feature1.id}")
    print(f"  Title: {feature1.title}")
    print(f"  Status: {feature1.status}")
    print(f"  Priority: {feature1.priority}")
    print(f"  Steps: {len(feature1.steps)}")
    print()

    # Create Feature 2: 2 steps
    print("-" * 70)
    print("Creating Feature 2: Phase 4 Final Test Feature 2")
    print("-" * 70)

    feature2 = (
        sdk.features.create("Phase 4 Final Test Feature 2")
        .set_priority("medium")
        .add_steps(
            [
                "Step 1: Requirements gathering",
                "Step 2: Implementation and documentation",
            ]
        )
        .save()
    )

    print(f"Feature 2 created: {feature2.id}")
    print(f"  Title: {feature2.title}")
    print(f"  Status: {feature2.status}")
    print(f"  Priority: {feature2.priority}")
    print(f"  Steps: {len(feature2.steps)}")
    print()

    # Mark both as in_progress
    print("-" * 70)
    print("Marking features as in_progress")
    print("-" * 70)

    with sdk.features.edit(feature1.id) as f:
        f.status = "in_progress"
    print(f"Feature 1 marked as in_progress: {feature1.id}")

    with sdk.features.edit(feature2.id) as f:
        f.status = "in_progress"
    print(f"Feature 2 marked as in_progress: {feature2.id}")
    print()

    # Report completion
    print("=" * 70)
    print("COMPLETION REPORT")
    print("=" * 70)
    print()
    print("FEATURES CREATED:")
    print(f"  1. {feature1.id}: {feature1.title}")
    print("     - Status: in_progress")
    print("     - Steps: 3")
    print("     - Priority: high")
    print()
    print(f"  2. {feature2.id}: {feature2.title}")
    print("     - Status: in_progress")
    print("     - Steps: 2")
    print("     - Priority: medium")
    print()

    print("DELEGATION EVENT TESTING:")
    print("  - SDK created features with agent attribution")
    print("  - Both features marked as in_progress")
    print("  - Should generate delegation events in agent_collaboration table")
    print()

    # Verify features exist and fetch them
    print("-" * 70)
    print("VERIFICATION: Fetching created features")
    print("-" * 70)

    fetched_f1 = sdk.features.get(feature1.id)
    fetched_f2 = sdk.features.get(feature2.id)

    if fetched_f1:
        print(f"✓ Feature 1 verified: {fetched_f1.title} (status: {fetched_f1.status})")
    else:
        print(f"✗ Feature 1 NOT found: {feature1.id}")

    if fetched_f2:
        print(f"✓ Feature 2 verified: {fetched_f2.title} (status: {fetched_f2.status})")
    else:
        print(f"✗ Feature 2 NOT found: {feature2.id}")
    print()

    print("=" * 70)
    print("TEST COMPLETE - Check agent_collaboration table for delegation events")
    print("=" * 70)

    return feature1.id, feature2.id


if __name__ == "__main__":
    try:
        f1_id, f2_id = main()
        print()
        print(f"Created feature IDs: {f1_id}, {f2_id}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
