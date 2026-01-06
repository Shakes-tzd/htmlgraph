#!/usr/bin/env python3
"""
Create multiple features to generate delegation events for testing.

This script creates:
1. Feature: "Delegation Test Feature 1" with 3 steps
2. Feature: "Delegation Test Feature 2" with 4 steps
3. Feature: "Delegation Test Feature 3" with 2 steps

Each feature is:
- Marked as in_progress
- Has descriptive step titles
- Linked to a track
"""

from htmlgraph import SDK


def main():
    # Initialize SDK with delegation test agent
    sdk = SDK(agent="codex-delegation-test-run2")

    # Create or get track for linking features
    print("Creating test track...")
    track = (
        sdk.tracks.create("Delegation Test Track")
        .description("Track for testing delegation events")
        .save()
    )
    print(f"Track created: {track.id}")

    # Feature 1: 3 steps
    print("\nCreating Feature 1...")
    feature1 = (
        sdk.features.create("Delegation Test Feature 1")
        .set_priority("high")
        .set_status("in-progress")
        .add_steps(
            [
                "Implement core delegation logic",
                "Add event logging for delegation",
                "Verify event tracking in database",
            ]
        )
        .set_track(track.id)
        .set_description("Test feature 1 for delegation event generation")
        .save()
    )
    print(f"Feature 1 created: {feature1.id}")

    # Feature 2: 4 steps
    print("\nCreating Feature 2...")
    feature2 = (
        sdk.features.create("Delegation Test Feature 2")
        .set_priority("medium")
        .set_status("in-progress")
        .add_steps(
            [
                "Design delegation workflow",
                "Create delegation request builder",
                "Implement delegation handler",
                "Add delegation validation rules",
            ]
        )
        .set_track(track.id)
        .set_description("Test feature 2 for delegation event generation")
        .save()
    )
    print(f"Feature 2 created: {feature2.id}")

    # Feature 3: 2 steps
    print("\nCreating Feature 3...")
    feature3 = (
        sdk.features.create("Delegation Test Feature 3")
        .set_priority("low")
        .set_status("in-progress")
        .add_steps(["Document delegation patterns", "Create delegation test suite"])
        .set_track(track.id)
        .set_description("Test feature 3 for delegation event generation")
        .save()
    )
    print(f"Feature 3 created: {feature3.id}")

    # Create spike to report findings
    print("\nCreating spike to report findings...")
    spike = (
        sdk.spikes.create("Delegation Test Run 2")
        .set_findings(f"""
Delegation Events Test Run 2 - Created 3 features to generate delegation events for testing.

Features Created:
1. Delegation Test Feature 1 (ID: {feature1.id}) - Status: in-progress - Steps: 3 - Track: {track.id}
2. Delegation Test Feature 2 (ID: {feature2.id}) - Status: in-progress - Steps: 4 - Track: {track.id}
3. Delegation Test Feature 3 (ID: {feature3.id}) - Status: in-progress - Steps: 2 - Track: {track.id}

Track: ID {track.id} - Title: Delegation Test Track

Expected delegation events in agent_collaboration table:
- Feature creation events
- Feature status changes
- Track linking events
- Step completion tracking
""")
        .save()
    )
    print(f"Spike created: {spike.id}")

    # Print summary
    print("\n" + "=" * 60)
    print("DELEGATION TEST FEATURES CREATED")
    print("=" * 60)
    print(f"Track ID: {track.id}")
    print(f"Feature 1 ID: {feature1.id}")
    print(f"Feature 2 ID: {feature2.id}")
    print(f"Feature 3 ID: {feature3.id}")
    print(f"Spike ID: {spike.id}")
    print("\nThese features should generate delegation events that can be")
    print("tracked in the agent_collaboration table.")


if __name__ == "__main__":
    main()
