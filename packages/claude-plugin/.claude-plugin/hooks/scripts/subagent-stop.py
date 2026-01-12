#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
SubagentStop Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.subagent_stop package module, which captures delegated
task completions when subagents spawned via Task() complete.
"""

from htmlgraph.hooks.subagent_stop import main

if __name__ == "__main__":
    main()
