#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
SubagentStop Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.subagent_stop package module, which updates parent events
when subagents complete.

Performance: Minimal overhead, graceful degradation on errors.
"""

from htmlgraph.hooks.subagent_stop import main

if __name__ == "__main__":
    main()
