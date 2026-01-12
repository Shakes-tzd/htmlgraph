#!/usr/bin/env python3
"""Update phase2-js-library feature to mark steps as completed."""

from htmlgraph import SDK

# Initialize SDK
sdk = SDK(agent="claude")

# Edit the feature to mark all steps as completed
with sdk.features.edit("phase2-js-library") as feature:
    # Mark all steps as completed
    for i, step in enumerate(feature.steps):
        step.completed = True
        step.agent = "claude"
        print(f"✅ Marked step {i} as completed: {step.description}")

    # Update status to done
    feature.status = "done"
    print("\n✅ Updated feature status to 'done'")

print("\n✅ Feature 'phase2-js-library' updated successfully!")
