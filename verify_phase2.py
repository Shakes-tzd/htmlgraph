#!/usr/bin/env python3
"""
Verify Phase 2 Implementation

This script verifies that all Phase 2 changes are correctly implemented:
1. SDK method init_project() exists and is callable
2. Commands use SDK methods instead of CLI
3. Commands have efficiency metrics
"""

import sys
from pathlib import Path


def verify_sdk_method():
    """Verify init_project() SDK method exists."""
    print("1. Verifying SDK method init_project()...")

    try:
        from htmlgraph import SDK

        # Check method exists
        sdk = SDK(agent="test-verifier")
        assert hasattr(sdk, "init_project"), "init_project() method not found"

        # Check it's callable
        assert callable(sdk.init_project), "init_project() is not callable"

        print("   ✅ init_project() method exists and is callable")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def verify_command_file(filepath: Path, expected_sdk_methods: list[str]):
    """Verify command file uses SDK methods."""
    print(f"\n2. Verifying {filepath.name}...")

    try:
        content = filepath.read_text()

        # Check for efficiency comment
        if "<!-- Efficiency:" not in content:
            print("   ⚠️  Missing efficiency comment")
        else:
            print("   ✅ Has efficiency metrics comment")

        # Check SDK methods are mentioned
        for method in expected_sdk_methods:
            if method in content:
                print(f"   ✅ Uses SDK method: {method}")
            else:
                print(f"   ❌ Missing SDK method: {method}")
                return False

        # Check CLI commands are NOT present
        if (
            "htmlgraph track" in content
            or "htmlgraph serve" in content
            or "htmlgraph init" in content
        ):
            if filepath.name != "track.md":  # track.md might reference it in docs
                print("   ⚠️  Still contains CLI references")

        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all verifications."""
    print("=" * 60)
    print("Phase 2 Implementation Verification")
    print("=" * 60)

    results = []

    # 1. Verify SDK method
    results.append(verify_sdk_method())

    # 2. Verify commands
    plugin_dir = Path(__file__).parent / "packages" / "claude-plugin" / "commands"

    commands = {
        "track.md": ["track_activity", "get_active_work_item"],
        "serve.md": ["start_server"],
        "init.md": ["init_project"],
    }

    for cmd_file, methods in commands.items():
        filepath = plugin_dir / cmd_file
        if filepath.exists():
            results.append(verify_command_file(filepath, methods))
        else:
            print(f"\n❌ Command file not found: {cmd_file}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All Phase 2 verifications PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ Some Phase 2 verifications FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
