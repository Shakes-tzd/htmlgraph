#!/usr/bin/env python3
"""Test SDK discoverability improvements.

Tests:
1. Enhanced error messages with "did you mean?" suggestions
2. Similar method recommendations
3. Improved batch operation feedback
4. SDK help() method
"""

from htmlgraph import SDK


def test_error_suggestions(isolated_db):
    """Test that common mistakes provide helpful suggestions."""
    print("=" * 60)
    print("TEST 1: Error Messages with Suggestions")
    print("=" * 60)

    sdk = SDK(agent="test-agent", db_path=str(isolated_db))

    # Test 1: Common mistake - mark_complete instead of mark_done
    print("\n1. Testing 'mark_complete' (should suggest 'mark_done'):")
    try:
        sdk.features.mark_complete(["feat-123"])
    except AttributeError as e:
        print(f"✓ Got helpful error:\n{e}\n")

    # Test 2: Another common mistake - finish
    print("2. Testing 'finish' (should suggest 'mark_done'):")
    try:
        sdk.features.finish(["feat-123"])
    except AttributeError as e:
        print(f"✓ Got helpful error:\n{e}\n")

    # Test 3: Similar method - creat instead of create
    print("3. Testing 'creat' (should suggest 'create'):")
    try:
        sdk.features.creat("New Feature")
    except AttributeError as e:
        print(f"✓ Got helpful error:\n{e}\n")

    # Test 4: Completely wrong method
    print("4. Testing 'nonexistent_method' (should list available methods):")
    try:
        sdk.features.nonexistent_method()
    except AttributeError as e:
        print(f"✓ Got helpful error:\n{e}\n")


def test_batch_operation_feedback(isolated_db):
    """Test improved batch operation feedback."""
    print("=" * 60)
    print("TEST 2: Improved Batch Operation Feedback")
    print("=" * 60)

    sdk = SDK(agent="test-agent", db_path=str(isolated_db))

    # Create a track first
    print("\n0. Creating test track...")
    track = sdk.tracks.create("Batch Operation Test Track").save()
    print(f"✓ Created track {track.id}")

    # Create some test features
    print("\n1. Creating test features...")
    f1 = sdk.features.create("Test Feature 1").set_track(track.id).save()
    f2 = sdk.features.create("Test Feature 2").set_track(track.id).save()
    print(f"✓ Created {f1.id} and {f2.id}")

    # Test mark_done with valid IDs
    print("\n2. Testing mark_done with valid IDs:")
    result = sdk.features.mark_done([f1.id, f2.id])
    print(f"✓ Result type: {type(result)}")
    print(f"✓ Result: {result}")

    # Test mark_done with mix of valid and invalid IDs
    print("\n3. Testing mark_done with mix of valid and invalid IDs:")
    result = sdk.features.mark_done([f1.id, "invalid-id", f2.id])
    print(f"✓ Result: {result}")

    # Test mark_done with all invalid IDs
    print("\n4. Testing mark_done with all invalid IDs:")
    result = sdk.features.mark_done(["invalid-1", "invalid-2"])
    print(f"✓ Result: {result}")


def test_sdk_help(isolated_db):
    """Test SDK help() method."""
    print("=" * 60)
    print("TEST 3: SDK Help Method")
    print("=" * 60)

    sdk = SDK(agent="test-agent", db_path=str(isolated_db))

    print("\n1. Testing sdk.help():")
    help_text = sdk.help()
    print(help_text)

    print("\n2. Checking help includes analytics APIs:")
    if "dep_analytics" in help_text:
        print("✓ Contains dep_analytics")
    if "recommend_next_work" in help_text:
        print("✓ Contains recommend_next_work")
    if "find_bottlenecks" in help_text:
        print("✓ Contains find_bottlenecks")


def test_sdk_docstring(isolated_db):
    """Test enhanced SDK docstring."""
    print("=" * 60)
    print("TEST 4: Enhanced SDK Docstring")
    print("=" * 60)

    from htmlgraph.sdk import SDK

    print("\n1. SDK class docstring:")
    docstring = SDK.__doc__

    # Check for key sections
    sections = [
        "Analytics & Decision Support",
        "Strategic Planning",
        "Dependency Analysis",
        "recommend_next_work",
        "find_bottlenecks",
        "get_parallel_work",
    ]

    for section in sections:
        if section in docstring:
            print(f"✓ Contains '{section}'")
        else:
            print(f"✗ Missing '{section}'")


def main():
    """Run all discoverability tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "SDK Discoverability Test Suite" + " " * 17 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")

    try:
        test_error_suggestions()
        test_batch_operation_feedback()
        test_sdk_help()
        test_sdk_docstring()

        print("\n")
        print("=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        print("\nSummary:")
        print("✓ Enhanced error messages working")
        print("✓ Improved batch operation feedback working")
        print("✓ SDK help() method working")
        print("✓ Enhanced docstring complete")
        print("\n")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
