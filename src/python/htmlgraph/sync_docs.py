#!/usr/bin/env python3
"""
Memory File Synchronization Tool

Helps maintain consistency across AI agent memory files for a project.
Ensures platform-specific files (CLAUDE.md, GEMINI.md, etc.) reference
the central AGENTS.md documentation.

Usage:
    python scripts/sync_memory_files.py
    python scripts/sync_memory_files.py --check
    python scripts/sync_memory_files.py --generate gemini
"""

import argparse
import sys
from pathlib import Path

# Platform-specific file templates
PLATFORM_TEMPLATES = {
    "gemini": {
        "filename": "GEMINI.md",
        "title": "HtmlGraph for Gemini",
        "platform_name": "Google Gemini",
        "agent_id": "gemini",
        "notes": """### Using HtmlGraph with Gemini Code Assist

```python
from htmlgraph import SDK

# Initialize SDK
sdk = SDK(agent="gemini")

# Get project summary
print(sdk.summary(max_items=10))
```

### Gemini Extension Integration

The HtmlGraph Gemini extension is located at `packages/gemini-extension/`.
""",
    },
    "claude": {
        "filename": "CLAUDE.md",
        "title": "HtmlGraph for Claude",
        "platform_name": "Anthropic Claude",
        "agent_id": "claude",
        "notes": """### Using HtmlGraph with Claude Code

```python
from htmlgraph import SDK

# Initialize SDK
sdk = SDK(agent="claude")

# Get project summary
print(sdk.summary(max_items=10))
```

### Claude Plugin Integration

The HtmlGraph Claude plugin is located at `packages/claude-plugin/`.
""",
    },
    "codex": {
        "filename": "CODEX.md",
        "title": "HtmlGraph for Codex",
        "platform_name": "GitHub Codex",
        "agent_id": "codex",
        "notes": """### Using HtmlGraph with Codex

```python
from htmlgraph import SDK

# Initialize SDK
sdk = SDK(agent="codex")

# Get project summary
print(sdk.summary(max_items=10))
```

### Codex Skill Integration

The HtmlGraph Codex skill is located at `packages/codex-skill/`.
""",
    },
}


def generate_platform_file(platform: str, project_root: Path) -> str:
    """Generate a platform-specific memory file that references AGENTS.md."""
    template = PLATFORM_TEMPLATES.get(platform.lower())
    if not template:
        raise ValueError(
            f"Unknown platform: {platform}. Available: {', '.join(PLATFORM_TEMPLATES.keys())}"
        )

    content = f"""# {template["title"]}

**Platform-specific instructions for {template["platform_name"]} AI agents.**

---

## Core Documentation

**→ See [AGENTS.md](./AGENTS.md) for complete AI agent documentation**

The main AGENTS.md file contains:
- Python SDK quick start
- API and CLI alternatives
- Best practices for AI agents
- Complete workflow examples
- Deployment instructions
- API reference

---

## {template["platform_name"]}-Specific Notes

{template["notes"]}

---

## Commands Available in {template["platform_name"]}

All HtmlGraph commands are available through the extension/plugin:

- `/htmlgraph:start` - Start session with project context
- `/htmlgraph:status` - Check current status
- `/htmlgraph:plan` - Smart planning workflow
- `/htmlgraph:spike` - Create research spike
- `/htmlgraph:recommend` - Get strategic recommendations
- `/htmlgraph:end` - End session with summary

**→ Full command reference in [AGENTS.md](./AGENTS.md)**

---

## Documentation

- **Main Guide**: [AGENTS.md](./AGENTS.md) - Complete AI agent documentation
- **Deployment**: [AGENTS.md#deployment--release](./AGENTS.md#deployment--release)
- **SDK Reference**: `docs/SDK_FOR_AI_AGENTS.md`

---

**→ For complete documentation, see [AGENTS.md](./AGENTS.md)**
"""
    return content


def check_file_references_agents(filepath: Path) -> bool:
    """Check if a platform file references AGENTS.md."""
    if not filepath.exists():
        return False

    content = filepath.read_text()
    return "AGENTS.md" in content


def check_all_files(project_root: Path) -> dict[str, bool]:
    """Check all platform files for AGENTS.md references."""
    results = {}

    # Check AGENTS.md exists (required)
    agents_file = project_root / "AGENTS.md"
    results["AGENTS.md"] = agents_file.exists()

    # Check root-level platform files
    for platform, template in PLATFORM_TEMPLATES.items():
        filepath = project_root / template["filename"]
        if filepath.exists():
            has_reference = check_file_references_agents(filepath)
            results[f"root:{template['filename']}"] = has_reference

    # Check package-specific skill files (actual locations)
    skill_files = {
        "claude-plugin": project_root
        / "packages/claude-plugin/skills/htmlgraph-tracker/SKILL.md",
        "gemini-extension": project_root / "packages/gemini-extension/GEMINI.md",
        "codex-skill": project_root / "packages/codex-skill/SKILL.md",
    }

    for platform_name, filepath in skill_files.items():
        if filepath.exists():
            has_reference = check_file_references_agents(filepath)
            results[f"package:{platform_name}"] = has_reference

    return results


def sync_all_files(project_root: Path, dry_run: bool = False) -> list[str]:
    """Synchronize all platform files to reference AGENTS.md."""
    changes = []

    # Ensure AGENTS.md exists
    agents_file = project_root / "AGENTS.md"
    if not agents_file.exists():
        changes.append("⚠️  AGENTS.md not found - create it first!")
        return changes

    # Check each platform file
    for platform, template in PLATFORM_TEMPLATES.items():
        filepath = project_root / template["filename"]

        if filepath.exists():
            # Check if it references AGENTS.md
            if not check_file_references_agents(filepath):
                changes.append(
                    f"⚠️  {template['filename']} exists but doesn't reference AGENTS.md"
                )
                changes.append(
                    f"   → Add reference manually or regenerate with --generate {platform}"
                )
        else:
            changes.append(f"ℹ️  {template['filename']} not found (optional)")

    if not changes:
        changes.append("✅ All files are synchronized!")

    return changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize AI agent memory files for a project"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are synchronized (no changes)",
    )
    parser.add_argument(
        "--generate",
        metavar="PLATFORM",
        help=f"Generate a platform-specific file ({', '.join(PLATFORM_TEMPLATES.keys())})",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files when generating",
    )

    args = parser.parse_args()

    project_root = args.project_root.resolve()

    if args.check:
        # Check mode
        print("🔍 Checking memory files...")
        results = check_all_files(project_root)

        print("\nStatus:")
        all_good = True
        for filename, status in results.items():
            if filename == "AGENTS.md":
                if status:
                    print(f"  ✅ {filename} exists")
                else:
                    print(f"  ❌ {filename} MISSING (required)")
                    all_good = False
            else:
                if status:
                    print(f"  ✅ {filename} references AGENTS.md")
                else:
                    print(f"  ⚠️  {filename} exists but doesn't reference AGENTS.md")
                    all_good = False

        if all_good:
            print("\n✅ All files are properly synchronized!")
            return 0
        else:
            print("\n⚠️  Some files need attention")
            return 1

    elif args.generate:
        # Generate mode
        platform = args.generate.lower()
        print(f"📝 Generating {platform.upper()} memory file...")

        try:
            content = generate_platform_file(platform, project_root)
            template = PLATFORM_TEMPLATES[platform]
            filepath = project_root / template["filename"]

            if filepath.exists() and not args.force:
                print(f"⚠️  {filepath.name} already exists. Use --force to overwrite.")
                return 1

            filepath.write_text(content)
            print(f"✅ Created: {filepath}")
            print("\nThe file references AGENTS.md for core documentation.")
            return 0

        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1

    else:
        # Sync mode (default)
        print("🔄 Synchronizing memory files...")
        changes = sync_all_files(project_root)

        print("\nResults:")
        for change in changes:
            print(f"  {change}")

        # Return non-zero if issues found
        return 1 if any("⚠️" in c or "❌" in c for c in changes) else 0


if __name__ == "__main__":
    sys.exit(main())
