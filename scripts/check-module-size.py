#!/usr/bin/env python3
"""Module size and complexity enforcement script.

Checks Python modules against industry-standard size limits:
- Module line count: warn >300, fail >500 (new modules), critical >1000
- Function length: warn >30, fail >50
- Class length: warn >200, fail >300

Usage:
    python scripts/check-module-size.py                    # Check all modules
    python scripts/check-module-size.py --changed-only     # Check only git-changed files
    python scripts/check-module-size.py --fail-on-warning  # Strict mode
    python scripts/check-module-size.py --json             # JSON output
    python scripts/check-module-size.py --summary          # Summary table only
    python scripts/check-module-size.py path/to/file.py    # Check specific files

Exit codes:
    0 - All checks pass
    1 - Warnings found (non-blocking by default)
    2 - Failures found (blocking)
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- Configuration ---

SRC_DIR = Path("src/python/htmlgraph")

# Module line count thresholds
MODULE_WARN = 300
MODULE_FAIL = 500
MODULE_CRITICAL = 1000

# Function line count thresholds
FUNCTION_WARN = 30
FUNCTION_FAIL = 50

# Class line count thresholds
CLASS_WARN = 200
CLASS_FAIL = 300

# Grandfathered modules: these existed before standards were enforced.
# They are tracked but don't cause failures. Any modification must not
# increase their size. Remove entries as modules are refactored.
GRANDFATHERED_MODULES: set[str] = {
    "session_manager.py",
    "models.py",
    "graph.py",
    "hooks/event_tracker.py",
    "session_context.py",
    "cli/analytics.py",
    "server.py",
    "api/services.py",
    "cli/core.py",
    "hooks/pretooluse.py",
    "api/routes/dashboard.py",
    "cli/work/ingest.py",
    "planning/models.py",
    "planning.py",
    "agents.py",
}


@dataclass
class Issue:
    file: str
    kind: str  # "module", "function", "class"
    name: str
    lines: int
    level: str  # "warning", "failure", "critical"
    threshold: int
    grandfathered: bool = False


@dataclass
class FileReport:
    path: str
    total_lines: int
    functions: list[tuple[str, int]] = field(default_factory=list)
    classes: list[tuple[str, int]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def count_lines(filepath: Path) -> int:
    """Count non-empty, non-comment lines in a Python file."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def analyze_ast(filepath: Path) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Extract function and class sizes from AST."""
    try:
        text = filepath.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(filepath))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return [], []

    functions: list[tuple[str, int]] = []
    classes: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            size = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
            functions.append((node.name, size))
        elif isinstance(node, ast.ClassDef):
            size = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
            classes.append((node.name, size))

    return functions, classes


def get_relative_path(filepath: Path) -> str:
    """Get path relative to SRC_DIR."""
    try:
        return str(filepath.relative_to(SRC_DIR))
    except ValueError:
        return str(filepath)


def is_grandfathered(rel_path: str) -> bool:
    """Check if a module is grandfathered."""
    return rel_path in GRANDFATHERED_MODULES


def check_file(filepath: Path) -> FileReport:
    """Check a single file against all thresholds."""
    rel_path = get_relative_path(filepath)
    total_lines = count_lines(filepath)
    functions, classes = analyze_ast(filepath)
    grandfathered = is_grandfathered(rel_path)

    report = FileReport(
        path=rel_path,
        total_lines=total_lines,
        functions=functions,
        classes=classes,
    )

    # Check module size
    if total_lines > MODULE_CRITICAL:
        report.issues.append(
            Issue(
                rel_path,
                "module",
                rel_path,
                total_lines,
                "critical",
                MODULE_CRITICAL,
                grandfathered,
            )
        )
    elif total_lines > MODULE_FAIL:
        report.issues.append(
            Issue(
                rel_path,
                "module",
                rel_path,
                total_lines,
                "failure",
                MODULE_FAIL,
                grandfathered,
            )
        )
    elif total_lines > MODULE_WARN:
        report.issues.append(
            Issue(
                rel_path,
                "module",
                rel_path,
                total_lines,
                "warning",
                MODULE_WARN,
                grandfathered,
            )
        )

    # Check function sizes
    for name, size in functions:
        if size > FUNCTION_FAIL:
            report.issues.append(
                Issue(rel_path, "function", name, size, "failure", FUNCTION_FAIL)
            )
        elif size > FUNCTION_WARN:
            report.issues.append(
                Issue(rel_path, "function", name, size, "warning", FUNCTION_WARN)
            )

    # Check class sizes
    for name, size in classes:
        if size > CLASS_FAIL:
            report.issues.append(
                Issue(rel_path, "class", name, size, "failure", CLASS_FAIL)
            )
        elif size > CLASS_WARN:
            report.issues.append(
                Issue(rel_path, "class", name, size, "warning", CLASS_WARN)
            )

    return report


def get_changed_files() -> list[Path]:
    """Get Python files changed in git (staged + unstaged)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = result.stdout.strip().splitlines()
        # Also check staged files
        result2 = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "--cached"],
            capture_output=True,
            text=True,
            check=True,
        )
        files.extend(result2.stdout.strip().splitlines())
        return [
            Path(f)
            for f in set(files)
            if f.startswith(str(SRC_DIR)) and f.endswith(".py")
        ]
    except subprocess.CalledProcessError:
        return []


def get_all_python_files() -> list[Path]:
    """Get all Python files in SRC_DIR."""
    return sorted(SRC_DIR.rglob("*.py"))


def print_summary(reports: list[FileReport]) -> None:
    """Print a summary table of oversized modules."""
    oversized = [r for r in reports if r.total_lines > MODULE_WARN]
    if not oversized:
        print("\nAll modules are within size limits.")
        return

    oversized.sort(key=lambda r: r.total_lines, reverse=True)

    print(f"\n{'Module':<55} {'Lines':>6} {'Status':<12} {'Note'}")
    print("-" * 90)
    for r in oversized:
        rel = r.path
        grandfathered = is_grandfathered(rel)

        if r.total_lines > MODULE_CRITICAL:
            status = "CRITICAL"
        elif r.total_lines > MODULE_FAIL:
            status = "FAIL"
        else:
            status = "WARN"

        note = "(grandfathered)" if grandfathered else ""
        print(f"{rel:<55} {r.total_lines:>6} {status:<12} {note}")

    total_over = len(oversized)
    critical = sum(1 for r in oversized if r.total_lines > MODULE_CRITICAL)
    failures = sum(
        1 for r in oversized if MODULE_FAIL < r.total_lines <= MODULE_CRITICAL
    )
    warnings = sum(1 for r in oversized if MODULE_WARN < r.total_lines <= MODULE_FAIL)

    print(
        f"\nTotal: {total_over} oversized modules ({critical} critical, {failures} failures, {warnings} warnings)"
    )


def print_issues(reports: list[FileReport], *, verbose: bool = True) -> None:
    """Print all issues found."""
    all_issues = []
    for r in reports:
        all_issues.extend(r.issues)

    if not all_issues:
        print("No issues found.")
        return

    # Group by level
    for level in ("critical", "failure", "warning"):
        level_issues = [
            i for i in all_issues if i.level == level and not i.grandfathered
        ]
        if not level_issues:
            continue

        icon = {"critical": "!!!", "failure": "XX", "warning": "~~"}[level]
        print(f"\n{icon} {level.upper()} ({len(level_issues)} issues):")
        for issue in sorted(level_issues, key=lambda i: -i.lines):
            print(
                f"  {issue.file}: {issue.kind} '{issue.name}' is {issue.lines} lines (limit: {issue.threshold})"
            )

    # Show grandfathered separately
    gf_issues = [i for i in all_issues if i.grandfathered]
    if gf_issues and verbose:
        print(f"\n** GRANDFATHERED ({len(gf_issues)} modules tracked for refactoring):")
        for issue in sorted(gf_issues, key=lambda i: -i.lines):
            print(f"  {issue.file}: {issue.lines} lines (target: <{MODULE_FAIL})")


def to_json(reports: list[FileReport]) -> str:
    """Convert reports to JSON."""
    data = {
        "thresholds": {
            "module": {
                "warn": MODULE_WARN,
                "fail": MODULE_FAIL,
                "critical": MODULE_CRITICAL,
            },
            "function": {"warn": FUNCTION_WARN, "fail": FUNCTION_FAIL},
            "class": {"warn": CLASS_WARN, "fail": CLASS_FAIL},
        },
        "summary": {
            "total_files": len(reports),
            "total_issues": sum(len(r.issues) for r in reports),
            "oversized_modules": sum(1 for r in reports if r.total_lines > MODULE_WARN),
        },
        "files": [
            {
                "path": r.path,
                "lines": r.total_lines,
                "issues": [
                    {
                        "kind": i.kind,
                        "name": i.name,
                        "lines": i.lines,
                        "level": i.level,
                        "threshold": i.threshold,
                        "grandfathered": i.grandfathered,
                    }
                    for i in r.issues
                ],
            }
            for r in reports
            if r.issues
        ],
    }
    return json.dumps(data, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Python module sizes against standards"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all)"
    )
    parser.add_argument(
        "--changed-only", action="store_true", help="Only check git-changed files"
    )
    parser.add_argument(
        "--fail-on-warning", action="store_true", help="Treat warnings as failures"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON"
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show summary table only"
    )
    parser.add_argument(
        "--no-grandfathered",
        action="store_true",
        help="Don't show grandfathered modules",
    )
    args = parser.parse_args()

    # Determine which files to check
    if args.files:
        files = [Path(f) for f in args.files if f.endswith(".py")]
    elif args.changed_only:
        files = get_changed_files()
        if not files:
            print("No changed Python files found.")
            return 0
    else:
        files = get_all_python_files()

    # Skip __init__.py and test files
    files = [f for f in files if f.name != "__init__.py" and "test" not in str(f)]

    # Analyze
    reports = [check_file(f) for f in files]

    # Output
    if args.json_output:
        print(to_json(reports))
    elif args.summary:
        print_summary(reports)
    else:
        print(f"Checked {len(reports)} Python modules in {SRC_DIR}/")
        print_summary(reports)
        print_issues(reports, verbose=not args.no_grandfathered)

    # Determine exit code
    non_gf_issues = [i for r in reports for i in r.issues if not i.grandfathered]

    has_failures = any(i.level in ("failure", "critical") for i in non_gf_issues)
    has_warnings = any(i.level == "warning" for i in non_gf_issues)

    if has_failures:
        return 2
    if has_warnings and args.fail_on_warning:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
