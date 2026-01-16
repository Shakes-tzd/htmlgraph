#!/usr/bin/env python3
"""Verify all tests use isolated databases.

Scans test files for SDK() calls that don't include db_path parameter.
These calls will cause tests to share the default database at
~/.htmlgraph/htmlgraph.db, leading to concurrency issues.

Usage:
    python scripts/verify_test_isolation.py
    python scripts/verify_test_isolation.py --fix  # Show migration examples

Exit codes:
    0: All SDK() calls use isolated databases
    1: Found unmigrated SDK() calls that need db_path parameter
"""

import ast
import sys
from pathlib import Path


def find_sdk_calls_without_db_path(test_file: Path) -> list[int]:
    """Find SDK() calls missing db_path parameter.

    Args:
        test_file: Path to test file to scan

    Returns:
        List of line numbers where SDK() calls are missing db_path
    """
    try:
        content = test_file.read_text()
    except UnicodeDecodeError:
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Check if this is an SDK() call
        is_sdk_call = False
        if isinstance(node.func, ast.Name) and node.func.id == "SDK":
            is_sdk_call = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "SDK":
            is_sdk_call = True

        if not is_sdk_call:
            continue

        # Check if db_path is in kwargs
        has_db_path = any(kw.arg == "db_path" for kw in node.keywords)

        if not has_db_path:
            violations.append(node.lineno)

    return violations


def scan_tests(test_dir: Path = Path("tests")) -> dict[str, list[int]]:
    """Scan all test files for violations.

    Args:
        test_dir: Root directory to scan for test files

    Returns:
        Dict mapping file paths to lists of line numbers with violations
    """
    violations = {}

    for test_file in sorted(test_dir.rglob("test_*.py")):
        issues = find_sdk_calls_without_db_path(test_file)
        if issues:
            violations[str(test_file)] = issues

    return violations


def count_files_and_calls(violations: dict[str, list[int]]) -> tuple[int, int]:
    """Count total files and SDK calls with violations.

    Args:
        violations: Dict of violations from scan_tests()

    Returns:
        Tuple of (num_files, num_calls)
    """
    num_files = len(violations)
    num_calls = sum(len(lines) for lines in violations.values())
    return num_files, num_calls


def print_migration_example() -> None:
    """Print example migration pattern for reference."""
    example = """
MIGRATION EXAMPLE:

Before (without db_path):
    def test_feature_creation():
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir()
            (graph_dir / "features").mkdir()

            sdk = SDK(directory=graph_dir, agent="test")
            feature = sdk.features.create("Test").save()
            assert feature.id

After (using fixture):
    def test_feature_creation(isolated_sdk):
        feature = isolated_sdk.features.create("Test").save()
        assert feature.id

Before (needs custom agent):
    def test_agent_attribution(tmp_path):
        graph_dir = tmp_path / ".htmlgraph"
        graph_dir.mkdir()

        sdk = SDK(directory=graph_dir, agent="custom-agent")
        # ... test code

After (composing fixtures):
    def test_agent_attribution(isolated_graph_dir, isolated_db):
        sdk = SDK(
            directory=isolated_graph_dir,
            agent="custom-agent",
            db_path=str(isolated_db)
        )
        # ... test code

Available fixtures in tests/python/conftest.py:
    - isolated_db: Isolated database path
    - isolated_graph_dir: Minimal .htmlgraph directory
    - isolated_graph_dir_full: Full .htmlgraph directory with all subdirs
    - isolated_sdk: Full SDK instance (most common)
    - isolated_sdk_minimal: Minimal SDK instance

See tests/python/conftest.py for full fixture documentation.
"""
    print(example)


def main() -> int:
    """Main entry point.

    Returns:
        0 if all tests are isolated, 1 if violations found
    """
    violations = scan_tests()

    if not violations:
        print("✅ All SDK() calls use isolated databases")
        return 0

    num_files, num_calls = count_files_and_calls(violations)
    print(
        f"⚠️  Found {num_calls} SDK() call(s) without db_path in {num_files} file(s):\n"
    )

    for file in sorted(violations.keys()):
        lines = sorted(violations[file])
        # Convert to absolute path first, then make relative
        try:
            file_path = Path(file)
            if not file_path.is_absolute():
                file_path = (Path.cwd() / file_path).resolve()
            relative_path = file_path.relative_to(Path.cwd())
        except ValueError:
            # If conversion fails, use the file path as-is
            relative_path = file
        print(f"{relative_path}:")
        for line in lines:
            print(f"  Line {line}: SDK() call missing db_path")
        print()

    # Show migration example
    print("Use --help for migration examples and fixture documentation.")
    print()
    print("Quick migration tips:")
    print("  1. For simple cases, use 'isolated_sdk' fixture")
    print("  2. For custom setup, compose 'isolated_graph_dir' + 'isolated_db'")
    print("  3. See conftest.py for fixture documentation")
    print()

    return 1


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print_migration_example()
        sys.exit(0)

    sys.exit(main())
