#!/usr/bin/env python3
"""
Fix mypy type annotation errors across the codebase.

Fixes:
1. SDK type references outside TYPE_CHECKING blocks → string references
2. logger.debug(file=...) → proper logging without file parameter
"""

import re
import sys
from pathlib import Path


def fix_sdk_type_annotations(content: str) -> tuple[str, int]:
    """
    Fix SDK type references to use string forward references.

    Returns: (fixed_content, number_of_changes)
    """
    changes = 0

    # Pattern 1: Function parameters with SDK type (not in quotes)
    # Match: def func(sdk: SDK) or def func(sdk: SDK | None)
    # Replace with: def func(sdk: "SDK") or def func(sdk: "SDK | None")
    pattern1 = r'(\bsdk:\s*)SDK(\s*\|?\s*None)?(\s*[,\)])'
    replacement1 = r'\1"SDK\2"\3'
    new_content, count1 = re.subn(pattern1, replacement1, content)
    changes += count1

    # Pattern 2: Variable type annotations with SDK (not in quotes)
    # Match: self._sdk: SDK | None
    # Replace with: self._sdk: "SDK | None"
    pattern2 = r'(:\s*)SDK(\s*\|\s*None)?(\s*=)'
    replacement2 = r'\1"SDK\2"\3'
    new_content, count2 = re.subn(pattern2, replacement2, new_content)
    changes += count2

    # Pattern 3: Return type annotations with SDK
    # Match: -> SDK:
    # Replace with: -> "SDK":
    pattern3 = r'(->\s*)SDK(\s*:)'
    replacement3 = r'\1"SDK"\2'
    new_content, count3 = re.subn(pattern3, replacement3, new_content)
    changes += count3

    return new_content, changes


def fix_logger_file_parameter(content: str) -> tuple[str, int]:
    """
    Remove file= parameter from logger.debug() calls.

    Returns: (fixed_content, number_of_changes)
    """
    changes = 0

    # Pattern: logger.debug(..., file=sys.stderr)
    # Remove the file=sys.stderr part
    pattern = r'(logger\.(?:debug|info|warning|error)\([^)]+),\s*file=sys\.stderr'
    replacement = r'\1'
    new_content, count = re.subn(pattern, replacement, content)
    changes += count

    return new_content, changes


def process_file(file_path: Path) -> bool:
    """
    Process a single Python file to fix type annotations.

    Returns: True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text()
        original_content = content

        # Apply fixes
        content, sdk_changes = fix_sdk_type_annotations(content)
        content, logger_changes = fix_logger_file_parameter(content)

        total_changes = sdk_changes + logger_changes

        if total_changes > 0:
            file_path.write_text(content)
            print(f"✅ {file_path}: {sdk_changes} SDK fixes, {logger_changes} logger fixes")
            return True

        return False
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Fix type annotations across all Python files in src/python/htmlgraph/"""
    src_dir = Path("src/python/htmlgraph")

    if not src_dir.exists():
        print(f"❌ Directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    # Get all Python files
    python_files = list(src_dir.rglob("*.py"))

    print(f"Processing {len(python_files)} Python files...\n")

    modified_files = 0
    for file_path in python_files:
        if process_file(file_path):
            modified_files += 1

    print(f"\n📊 Summary: Modified {modified_files}/{len(python_files)} files")

    if modified_files > 0:
        print("\n✅ Run 'uv run mypy src/python/htmlgraph/' to verify fixes")


if __name__ == "__main__":
    main()
