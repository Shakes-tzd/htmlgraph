"""
Orchestrator system prompt loading and management.

Centralizes logic for loading and combining orchestrator system prompts,
keeping CLI code clean and focused on invocation.
"""

import textwrap
from pathlib import Path


def get_orchestrator_prompt(include_dev_mode: bool = False) -> str:
    """
    Load and combine orchestrator system prompts.

    Args:
        include_dev_mode: If True, append development mode guidance

    Returns:
        Combined system prompt text ready for --append-system-prompt
    """
    package_dir = Path(__file__).parent.parent

    # Load base orchestrator prompt
    prompt_file = package_dir / "orchestrator-system-prompt-optimized.txt"
    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        # Fallback: minimal orchestrator guidance
        base_prompt = textwrap.dedent(
            """
            You are an AI orchestrator for HtmlGraph project development.

            CRITICAL DIRECTIVES:
            1. DELEGATE to spawner skills - do not implement directly
            2. CREATE work items before delegating (features, bugs, spikes)
            3. USE SDK for tracking - all work must be tracked in .htmlgraph/
            4. RESPECT dependencies - check blockers before starting

            Key Rules:
            - Exploration/Research → Skill(skill=".claude-plugin:gemini")
            - Code implementation → Skill(skill=".claude-plugin:codex")
            - Git/GitHub ops → Skill(skill=".claude-plugin:copilot")
            - Strategic planning → Task() with Claude subagent

            Always use:
                from htmlgraph import SDK
                sdk = SDK(agent='orchestrator')

            See CLAUDE.md for complete orchestrator directives.
            """
        )

    # Load orchestration rules
    rules_file = package_dir / "orchestration.md"
    orchestration_rules = ""
    if rules_file.exists():
        orchestration_rules = rules_file.read_text(encoding="utf-8")

    # Combine prompts
    combined_prompt = base_prompt
    if orchestration_rules:
        combined_prompt = f"{base_prompt}\n\n---\n\n{orchestration_rules}"

    # Add dev mode guidance if requested
    if include_dev_mode:
        dev_addendum = textwrap.dedent(
            """

            ═══════════════════════════════════════════════════════════
            🔧 DEVELOPMENT MODE - HtmlGraph Project
            ═══════════════════════════════════════════════════════════

            CRITICAL: Hooks load htmlgraph from PyPI, NOT local source!

            Development Workflow:
            1. Make changes to src/python/htmlgraph/
            2. Run tests: uv run pytest
            3. Deploy to PyPI: ./scripts/deploy-all.sh X.Y.Z --no-confirm
            4. Restart Claude Code (hooks auto-load new version from PyPI)
            5. Verify changes work correctly

            Why PyPI in Dev Mode?
            - Hooks use: #!/usr/bin/env -S uv run --with htmlgraph
            - Always pulls latest version from PyPI
            - Tests in production-like environment
            - No surprises when distributed to users
            - Single source of truth (PyPI package)

            Incremental Versioning:
            - Use patch versions: 0.26.2 → 0.26.3 → 0.26.4
            - No need to edit hook shebangs (always get latest)
            - Deploy frequently for rapid iteration

            Session ID Tracking (v0.26.3+):
            - PostToolUse hooks query for most recent UserQuery session
            - All events should share same session_id
            - Verify: See "Development Mode" section in CLAUDE.md

            Key References:
            - Development workflow: CLAUDE.md "Development Mode" section
            - Orchestrator patterns: /orchestrator-directives skill
            - Code quality: /code-quality skill
            - Deployment: /deployment-automation skill

            Remember: You're dogfooding HtmlGraph!
            - Use SDK to track your own work
            - Delegate to spawner agents (Gemini, Codex, Copilot)
            - Follow orchestration patterns
            - Test in production-like environment

            ═══════════════════════════════════════════════════════════
            """
        )
        combined_prompt += dev_addendum

    return combined_prompt


def get_prompt_summary() -> dict[str, str]:
    """
    Get summary of available prompt components.

    Returns:
        Dictionary with component names and their status
    """
    package_dir = Path(__file__).parent.parent

    prompt_file = package_dir / "orchestrator-system-prompt-optimized.txt"
    rules_file = package_dir / "orchestration.md"

    return {
        "base_prompt": "✓ Found" if prompt_file.exists() else "✗ Missing",
        "orchestration_rules": "✓ Found" if rules_file.exists() else "✗ Missing",
        "base_prompt_path": str(prompt_file),
        "rules_path": str(rules_file),
    }
