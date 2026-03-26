#!/usr/bin/env python3
"""Pre-commit hook: detect incomplete systematic changes.

Warns when a commit appears to be part of a systematic rename/replace/migrate
operation but leaves instances of the old term in the codebase.

Exit code is always 0 (warning only). Use --no-verify to suppress.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directories excluded from remaining-instance grep
EXCLUDED_DIRS = {
    ".htmlgraph",
    ".git",
    "node_modules",
    "dist",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "build",
    ".tox",
    "venv",
    ".venv",
}

# File extensions to scan (empty = all text files)
SCAN_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".txt",
    ".html",
    ".ex",
    ".exs",
}

# Patterns in commit message / diff that signal a systematic change
SYSTEMATIC_KEYWORDS = re.compile(
    r"\b(rename[sd]?|replac[eing]+|migrat[eing]+|refactor[ing]*|mov[eing]+)\b",
    re.IGNORECASE,
)

# Lines in diff to skip — these are removals or meta-lines, not additions
_DIFF_SKIP_LINE_RE = re.compile(r"^(---|\+\+\+|@@|-)")

# False-positive patterns: lines that mention the old term but are comments
# explaining the change or TODO notes — safe to ignore
_FALSE_POSITIVE_RE = re.compile(
    r"(#\s*TODO[:\s].*rename|#\s*was\s+\w|#\s*old\s+name|#\s*formerly)",
    re.IGNORECASE,
)

# Maximum number of remaining-instances to show before truncating
MAX_INSTANCES_SHOWN = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    return result.stdout


def _git_root() -> Path:
    root = _run(["git", "rev-parse", "--show-toplevel"]).strip()
    return Path(root) if root else Path.cwd()


def _staged_diff() -> str:
    return _run(["git", "diff", "--cached", "--unified=0"])


def _commit_message() -> str:
    """Try to read COMMIT_EDITMSG if available (pre-commit runs before message)."""
    root = _git_root()
    msg_file = root / ".git" / "COMMIT_EDITMSG"
    if msg_file.exists():
        return msg_file.read_text(errors="replace")
    return ""


def _is_systematic(diff: str, msg: str) -> bool:
    return bool(SYSTEMATIC_KEYWORDS.search(diff) or SYSTEMATIC_KEYWORDS.search(msg))


def _extract_renamed_pairs(diff: str) -> list[tuple[str, str]]:
    """Extract (old_term, new_term) pairs from added lines in the diff.

    Strategy: for each added line that contains an identifier-like replacement,
    look for a paired removed line (same line offset or neighbouring hunk) and
    extract the differing token.  Falls back to scanning all added-line tokens
    that also appear in removed lines to find substitutions.
    """
    added_lines: list[str] = []
    removed_lines: list[str] = []

    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines.append(line[1:])

    # Tokenise: snake_case / CamelCase / kebab-case identifiers
    token_re = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")

    added_tokens: set[str] = set()
    removed_tokens: set[str] = set()

    for line in added_lines:
        added_tokens.update(token_re.findall(line))
    for line in removed_lines:
        removed_tokens.update(token_re.findall(line))

    # Old terms = tokens only in removed side (disappeared from codebase in this commit)
    # New terms = tokens only in added side (appeared in codebase in this commit)
    old_only = removed_tokens - added_tokens
    new_only = added_tokens - removed_tokens

    # Filter out very short or common words unlikely to be identifiers
    skip = {
        "the",
        "and",
        "for",
        "not",
        "are",
        "was",
        "has",
        "had",
        "but",
        "can",
        "use",
        "get",
        "set",
        "new",
        "old",
        "int",
        "str",
        "def",
        "cls",
        "self",
        "None",
        "True",
        "False",
        "import",
        "from",
        "class",
        "return",
        "yield",
    }

    pairs: list[tuple[str, str]] = []
    for old in sorted(old_only):
        if old in skip or len(old) < 4:
            continue
        # Pair with most similar new token (naive: same length ±3)
        candidates = [n for n in new_only if abs(len(n) - len(old)) <= 3]
        if candidates:
            pairs.append((old, candidates[0]))
        else:
            # No pairing candidate — still worth checking old term alone
            pairs.append((old, ""))

    return pairs


def _build_exclude_args() -> list[str]:
    args: list[str] = []
    for d in EXCLUDED_DIRS:
        args += ["--exclude-dir", d]
    return args


def _grep_remaining(term: str, root: Path) -> list[str]:
    """Return file:line matches for `term` in the working tree."""
    ext_args: list[str] = []
    for ext in SCAN_EXTENSIONS:
        ext_args += ["--include", f"*{ext}"]

    cmd = (
        ["grep", "-rn", "--color=never"]
        + _build_exclude_args()
        + ext_args
        + [term, str(root)]
    )
    output = _run(cmd)
    lines = [l for l in output.splitlines() if l.strip()]

    # Strip absolute path prefix to show relative paths
    rel_lines: list[str] = []
    for line in lines:
        if line.startswith(str(root)):
            line = line[len(str(root)) + 1 :]
        # Filter known false positives
        if not _FALSE_POSITIVE_RE.search(line):
            rel_lines.append(line)

    return rel_lines


def _format_warning(old_term: str, instances: list[str]) -> str:
    shown = instances[:MAX_INSTANCES_SHOWN]
    truncated = len(instances) - len(shown)
    lines = [
        "",
        f"  WARNING: Systematic change detected — '{old_term}' still appears in {len(instances)} location(s):",
    ]
    for inst in shown:
        lines.append(f"    {inst}")
    if truncated:
        lines.append(f"    ... and {truncated} more.")
    lines.append(
        "  If this is intentional, commit with --no-verify to skip this check."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    diff = _staged_diff()
    if not diff:
        return 0

    msg = _commit_message()

    if not _is_systematic(diff, msg):
        return 0

    root = _git_root()
    pairs = _extract_renamed_pairs(diff)

    if not pairs:
        return 0

    warnings: list[str] = []
    for old_term, _new_term in pairs:
        remaining = _grep_remaining(old_term, root)
        if remaining:
            warnings.append(_format_warning(old_term, remaining))

    if warnings:
        print(
            "\n[pre-commit-systematic-check] Potential incomplete systematic change:",
            file=sys.stderr,
        )
        for w in warnings:
            print(w, file=sys.stderr)
        print("", file=sys.stderr)

    # Always exit 0 — warning only
    return 0


if __name__ == "__main__":
    sys.exit(main())
