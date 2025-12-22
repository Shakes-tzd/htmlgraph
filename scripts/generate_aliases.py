#!/usr/bin/env python3
"""
Generate shell aliases for HtmlGraph commands.
Usage: python3 scripts/generate_aliases.py
"""

ALIASES = {
    "hg-start": "uv run htmlgraph session resume",  # The new unified start workflow
    "hg-resume": "uv run htmlgraph session resume",
    "hg-status": "uv run htmlgraph status",
    "hg-feat": "uv run htmlgraph feature list",
    "hg-feat-new": "uv run htmlgraph feature create",
    "hg-feat-start": "uv run htmlgraph feature start",
    "hg-feat-done": "uv run htmlgraph feature complete",
    "hg-feat-claim": "uv run htmlgraph feature claim",
    "hg-feat-release": "uv run htmlgraph feature release",
    "hg-track": "uv run htmlgraph activity", # Legacy mapping
    "hg-serve": "uv run htmlgraph serve",
}

def generate_bash():
    print("# HtmlGraph Aliases (Bash/Zsh)")
    print("# Source this file: source htmlgraph-aliases.sh")
    print("")
    for alias, command in ALIASES.items():
        print(f"alias {alias}='{command}'")

if __name__ == "__main__":
    generate_bash()
