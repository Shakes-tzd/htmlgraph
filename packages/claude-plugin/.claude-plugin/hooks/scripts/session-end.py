#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
SessionEnd Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.session_handler package module, which handles session
completion, handoff notes, and cleanup when a Claude Code session ends.
"""

from htmlgraph.hooks.session_handler import main

if __name__ == "__main__":
    main()
