#!/usr/bin/env python3
"""
Generate delegation events for testing.

Creates 3 features with different step counts, marks them as in_progress,
links them to a track, and reports to HtmlGraph via spike.
"""

from htmlgraph import SDK


def main():
    # Initialize SDK with explicit agent name
    sdk = SDK(agent="codex-delegation-test-run2")

    print("Creating delegation test features...")

    # Create a track first
    print("\n1. Creating track...")
    track = sdk.tracks.create(
        title="Delegation Test Track", description="Track for testing delegation events"
    ).save()
    print(f"   Created track: {track.id}")

    # Feature 1: 3 steps
    print("\n2. Creating Feature 1 (3 steps)...")
    feature1 = (
        sdk.features.create(
            title="Delegation Test Feature 1",
            description="First test feature with 3 steps",
        )
        .add_steps(
            [
                "Step 1: Research delegation architecture",
                "Step 2: Implement delegation handler",
                "Step 3: Write delegation tests",
            ]
        )
        .set_priority("high")
        .set_status("in_progress")
        .save()
    )
    print(f"   Created feature: {feature1.id}")
    print(f"   Status: {feature1.status}")
    print(f"   Steps: {len(feature1.steps)}")

    # Feature 2: 4 steps
    print("\n3. Creating Feature 2 (4 steps)...")
    feature2 = (
        sdk.features.create(
            title="Delegation Test Feature 2",
            description="Second test feature with 4 steps",
        )
        .add_steps(
            [
                "Step 1: Design delegation protocol",
                "Step 2: Build delegation framework",
                "Step 3: Integrate with orchestrator",
                "Step 4: Document delegation patterns",
            ]
        )
        .set_priority("medium")
        .set_status("in_progress")
        .save()
    )
    print(f"   Created feature: {feature2.id}")
    print(f"   Status: {feature2.status}")
    print(f"   Steps: {len(feature2.steps)}")

    # Feature 3: 2 steps
    print("\n4. Creating Feature 3 (2 steps)...")
    feature3 = (
        sdk.features.create(
            title="Delegation Test Feature 3",
            description="Third test feature with 2 steps",
        )
        .add_steps(
            ["Step 1: Validate delegation events", "Step 2: Collect delegation metrics"]
        )
        .set_priority("low")
        .set_status("in_progress")
        .save()
    )
    print(f"   Created feature: {feature3.id}")
    print(f"   Status: {feature3.status}")
    print(f"   Steps: {len(feature3.steps)}")

    # Report to HtmlGraph
    print("\n5. Creating HtmlGraph spike report...")
    spike = (
        sdk.spikes.create(title="Delegation Test Run 2")
        .set_findings(
            "Created 3 features to generate delegation events.\n\n"
            "Features Created:\n"
            f"1. {feature1.title} (ID: {feature1.id})\n"
            f"   - Steps: {len(feature1.steps)}\n"
            f"   - Status: {feature1.status}\n"
            f"   - Priority: {feature1.priority}\n\n"
            f"2. {feature2.title} (ID: {feature2.id})\n"
            f"   - Steps: {len(feature2.steps)}\n"
            f"   - Status: {feature2.status}\n"
            f"   - Priority: {feature2.priority}\n\n"
            f"3. {feature3.title} (ID: {feature3.id})\n"
            f"   - Steps: {len(feature3.steps)}\n"
            f"   - Status: {feature3.status}\n"
            f"   - Priority: {feature3.priority}\n\n"
            f"Track: {track.title} (ID: {track.id})\n\n"
            "These delegation events should be recorded in the agent_collaboration table.\n"
            "Agent: codex-delegation-test-run2"
        )
        .save()
    )
    print(f"   Created spike: {spike.id}")

    print("\n✅ Delegation test run complete!")
    print("\nCreated items:")
    print(f"  - Track: {track.id} ({track.title})")
    print(f"  - Feature 1: {feature1.id} ({feature1.title})")
    print(f"  - Feature 2: {feature2.id} ({feature2.title})")
    print(f"  - Feature 3: {feature3.id} ({feature3.title})")
    print(f"  - Spike Report: {spike.id} ({spike.title})")

    # Query the created features to verify
    print("\n📊 Verifying created features...")
    all_features = sdk.features.where(status="in_progress")
    print(f"   Total in_progress features: {len(all_features)}")

    for feat in all_features[-3:]:  # Show last 3
        print(f"   - {feat.title}: {len(feat.steps)} steps")


if __name__ == "__main__":
    main()
