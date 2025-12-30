#!/usr/bin/env python3
"""
Generate platform-specific command files from YAML definitions.

Single source of truth → Multiple platform outputs.

Usage:
    python generate_commands.py [--platform claude|codex|gemini|all]
"""

import argparse
from pathlib import Path
from typing import Any

import yaml


def load_command_definition(yaml_file: Path) -> dict[str, Any]:
    """Load command definition from YAML file."""
    with open(yaml_file) as f:
        return yaml.safe_load(f)


def generate_claude_code_command(cmd: dict[str, Any], output_dir: Path) -> None:
    """Generate Claude Code .md command file."""

    # Build parameters section
    params_md = ""
    for param in cmd.get("parameters", []):
        req_str = "required" if param.get("required", False) else "optional"
        default = f" (default: {param['default']})" if "default" in param else ""
        params_md += (
            f"- `{param['name']}` ({req_str}){default}: {param['description']}\n"
        )

    # Build examples section
    examples_md = ""
    for example in cmd.get("examples", []):
        examples_md += (
            f"```bash\n{example['command']}\n```\n{example['description']}\n\n"
        )

    # Generate markdown
    md_content = f"""# /htmlgraph:{cmd["name"]}

{cmd["short_description"]}

## Usage

```
{cmd["usage"].strip()}
```

## Parameters

{params_md}

## Examples

{examples_md}

## Instructions for Claude

This command uses the SDK's `{cmd["sdk_method"]}()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
{cmd["behavior"]["claude_code"].strip()}
```

### Output Format:

{cmd["output_template"].strip()}
"""

    # Write to file
    output_file = output_dir / f"{cmd['name']}.md"
    output_file.write_text(md_content)
    print(f"✓ Generated Claude Code command: {output_file}")


def generate_codex_command_section(cmd: dict[str, Any]) -> str:
    """Generate markdown section for Codex skill."""

    # Build examples
    examples_md = ""
    for example in cmd.get("examples", []):
        examples_md += f"- `{example['command']}` - {example['description']}\n"

    section = f"""
### `/{cmd["name"]}` - {cmd["short_description"]}

**Usage:** `{cmd["usage"].strip()}`

**Examples:**
{examples_md}

**SDK Method:** `sdk.{cmd["sdk_method"]}()`

```python
from htmlgraph import SDK

sdk = SDK(agent="codex")

{cmd["behavior"]["codex"].strip() if "codex" in cmd["behavior"] else cmd["behavior"]["claude_code"].replace('agent="claude"', 'agent="codex"').strip()}
```
"""
    return section


def generate_gemini_command_section(cmd: dict[str, Any]) -> str:
    """Generate markdown section for Gemini extension."""

    # Build examples
    examples_md = ""
    for example in cmd.get("examples", []):
        examples_md += f"- `{example['command']}` - {example['description']}\n"

    section = f"""
### `/{cmd["name"]}` - {cmd["short_description"]}

**Usage:** `{cmd["usage"].strip()}`

**Examples:**
{examples_md}

**SDK Method:** `sdk.{cmd["sdk_method"]}()`

```python
from htmlgraph import SDK

sdk = SDK(agent="gemini")

{cmd["behavior"]["gemini"].strip() if "gemini" in cmd["behavior"] else cmd["behavior"]["claude_code"].replace('agent="claude"', 'agent="gemini"').strip()}
```
"""
    return section


def append_to_skill_doc(sections: list[str], skill_file: Path, marker: str) -> None:
    """Append command sections to skill documentation after a marker."""

    # Read existing content
    content = skill_file.read_text()

    # Find marker or create new section
    if marker in content:
        # Insert before marker
        parts = content.split(marker)
        new_content = parts[0] + "\n".join(sections) + "\n\n" + marker + parts[1]
    else:
        # Append to end
        new_content = content + "\n\n## Planning Commands\n\n" + "\n".join(sections)

    # Write back
    skill_file.write_text(new_content)
    print(f"✓ Updated skill doc: {skill_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate platform-specific commands")
    parser.add_argument(
        "--platform",
        choices=["claude", "codex", "gemini", "all"],
        default="all",
        help="Target platform (default: all)",
    )
    args = parser.parse_args()

    # Paths
    root = Path(__file__).parent.parent.parent
    definitions_dir = root / "common" / "command_definitions"

    claude_output_dir = root / "claude-plugin" / "commands"
    # Note: codex_skill_file and gemini_doc_file removed - not currently used
    # Add back when implementing generation for these platforms

    # Load all command definitions
    command_files = sorted(definitions_dir.glob("*.yaml"))
    commands = [load_command_definition(f) for f in command_files]

    print(f"\nFound {len(commands)} command definitions")
    print("=" * 60)

    # Generate for each platform
    if args.platform in ["claude", "all"]:
        print("\n📦 Generating Claude Code commands...")
        claude_output_dir.mkdir(parents=True, exist_ok=True)
        for cmd in commands:
            generate_claude_code_command(cmd, claude_output_dir)

    if args.platform in ["codex", "all"]:
        print("\n📦 Generating Codex skill sections...")
        codex_sections = [generate_codex_command_section(cmd) for cmd in commands]
        # Note: Manual insertion for now - would need marker in SKILL.md
        for i, (cmd, section) in enumerate(zip(commands, codex_sections), 1):
            output_file = root / "codex-skill" / f"command_{cmd['name']}.md"
            output_file.write_text(section)
            print(f"✓ Generated Codex section: {output_file}")

    if args.platform in ["gemini", "all"]:
        print("\n📦 Generating Gemini extension sections...")
        gemini_sections = [generate_gemini_command_section(cmd) for cmd in commands]
        # Note: Manual insertion for now - would need marker in GEMINI.md
        for i, (cmd, section) in enumerate(zip(commands, gemini_sections), 1):
            output_file = root / "gemini-extension" / f"command_{cmd['name']}.md"
            output_file.write_text(section)
            print(f"✓ Generated Gemini section: {output_file}")

    print("\n" + "=" * 60)
    print("✅ Command generation complete!")
    print("\nNext steps:")
    print("1. Review generated command files")
    print("2. Manually integrate Codex/Gemini sections if needed")
    print("3. Add generation to build/publish workflow")


if __name__ == "__main__":
    main()
