#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
Stop Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.session_summary package module, which generates comprehensive
session summaries with CIGS analytics when a Claude Code session ends.
"""

from htmlgraph.hooks.session_summary import main

if __name__ == "__main__":
    main()
