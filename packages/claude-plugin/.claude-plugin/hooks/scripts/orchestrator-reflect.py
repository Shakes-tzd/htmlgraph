#!/usr/bin/env -S uv run --with htmlgraph>=0.26.5 python3
"""
Orchestrator Reflection Hook - Thin wrapper around package logic.

This script is a minimal entry point that delegates all logic to the
htmlgraph.hooks.orchestrator_reflector package module, which detects when
Claude executes Python code directly and provides gentle reflection prompts
to encourage delegation to subagents.
"""

from htmlgraph.hooks.orchestrator_reflector import main

if __name__ == "__main__":
    main()
