#!/usr/bin/env python3
"""
Migrate print() statements to Rich logging.

This script systematically replaces print() calls with logger.info/debug/warning/error.
"""

import re
import sys
from pathlib import Path


def has_logging_import(content: str) -> bool:
    """Check if file already imports logging."""
    return bool(re.search(r'^import logging\b', content, re.MULTILINE))


def has_logger_setup(content: str) -> bool:
    """Check if file already has logger setup."""
    return bool(re.search(r'logger\s*=\s*logging\.getLogger\(__name__\)', content))


def add_logging_imports(content: str) -> str:
    """Add logging imports if not present."""
    lines = content.split('\n')

    # Find the right place to insert imports (after docstring, before other imports)
    insert_idx = 0
    in_docstring = False
    docstring_closed = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Handle docstrings
        if not docstring_closed:
            if '"""' in stripped or "'''" in stripped:
                if in_docstring:
                    docstring_closed = True
                    insert_idx = i + 1
                else:
                    in_docstring = True
            continue

        # Skip empty lines and comments after docstring
        if not stripped or stripped.startswith('#'):
            insert_idx = i + 1
            continue

        # Found first real line - insert before it
        break

    # Check if logging is already imported
    if not has_logging_import(content):
        lines.insert(insert_idx, 'import logging\n')
        insert_idx += 1

    # Add logger setup after all imports
    if not has_logger_setup(content):
        # Find last import line
        last_import_idx = insert_idx
        for i in range(insert_idx, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith(('import ', 'from ')):
                last_import_idx = i
            elif stripped and not stripped.startswith('#'):
                break

        lines.insert(last_import_idx + 1, '\nlogger = logging.getLogger(__name__)\n')

    return '\n'.join(lines)


def classify_print_level(print_content: str, context: str) -> str:
    """Determine appropriate logging level based on print content."""
    lower = print_content.lower()

    if any(word in lower for word in ['error', 'failed', 'failure', 'exception', 'critical']):
        return 'error'
    elif any(word in lower for word in ['warning', 'warn', 'deprecated']):
        return 'warning'
    elif any(word in lower for word in ['debug', 'trace', 'verbose', 'watching', 'reloading']):
        return 'debug'
    else:
        return 'info'


def migrate_print_statement(match: re.Match, full_content: str) -> str:
    """Convert a single print() call to logger call."""
    indent = match.group(1)
    args = match.group(2)

    # Get context around the match for level determination
    start = max(0, match.start() - 200)
    end = min(len(full_content), match.end() + 200)
    context = full_content[start:end]

    # Determine logging level
    level = classify_print_level(args, context)

    # Handle different print() argument patterns
    # Case 1: f-string -> logger.info(f"...")
    if args.strip().startswith('f"') or args.strip().startswith("f'"):
        return f'{indent}logger.{level}({args.strip()})'

    # Case 2: Simple string -> logger.info("...")
    elif args.strip().startswith('"') or args.strip().startswith("'"):
        return f'{indent}logger.{level}({args.strip()})'

    # Case 3: Multiple arguments with formatting -> logger.info(f"...")
    elif ',' in args or '%' in args:
        # Complex case - keep as is for now, convert to f-string manually
        return f'{indent}logger.{level}({args.strip()})'

    # Case 4: Variable -> logger.info("%s", variable)
    else:
        return f'{indent}logger.{level}("%s", {args.strip()})'


def migrate_file(file_path: Path) -> tuple[bool, int]:
    """
    Migrate a single file from print() to logger.

    Returns:
        (changed, num_prints_replaced)
    """
    content = file_path.read_text()
    original = content

    # Count original prints
    original_prints = len(re.findall(r'\bprint\(', content))
    if original_prints == 0:
        return False, 0

    # Add logging imports and logger setup
    content = add_logging_imports(content)

    # Replace print() statements
    # Match: print(...) with proper nesting handling
    pattern = r'^(\s*)print\((.*?)\)\s*$'

    def replacer(match):
        return migrate_print_statement(match, content)

    content = re.sub(pattern, replacer, content, flags=re.MULTILINE)

    # Verify we replaced prints
    remaining_prints = len(re.findall(r'\bprint\(', content))
    replaced = original_prints - remaining_prints

    if content != original:
        file_path.write_text(content)
        return True, replaced

    return False, 0


def migrate_all_files(root_dir: Path) -> dict:
    """Migrate all Python files in directory."""
    results = {
        'files_changed': 0,
        'prints_replaced': 0,
        'files_processed': 0,
        'files_with_prints': []
    }

    for py_file in root_dir.rglob('*.py'):
        if '__pycache__' in str(py_file) or 'venv' in str(py_file):
            continue

        results['files_processed'] += 1
        changed, replaced = migrate_file(py_file)

        if changed:
            results['files_changed'] += 1
            results['prints_replaced'] += replaced
            results['files_with_prints'].append((str(py_file), replaced))

    return results


def main():
    """Run migration on src/python/htmlgraph directory."""
    root = Path(__file__).parent / 'src' / 'python' / 'htmlgraph'

    if not root.exists():
        print(f"Error: {root} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Migrating print() to logging in {root}...")
    results = migrate_all_files(root)

    print("\nMigration complete!")
    print(f"  Files processed: {results['files_processed']}")
    print(f"  Files changed: {results['files_changed']}")
    print(f"  Print statements replaced: {results['prints_replaced']}")

    if results['files_with_prints']:
        print("\nFiles modified:")
        for file_path, count in sorted(results['files_with_prints'], key=lambda x: -x[1])[:20]:
            print(f"  {file_path}: {count} prints")

    return 0 if results['files_changed'] > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
