#!/usr/bin/env python3
"""
HtmlGraph CLI Setup Commands

Automates setup of HtmlGraph for different AI CLI platforms:
- Claude Code (plugin via marketplace)
- Codex CLI (skill installation)
- Gemini CLI (extension installation)
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def run_command(
    cmd: list[str], capture: bool = False, check: bool = True
) -> subprocess.CompletedProcess[Any]:
    """Run a shell command."""
    result: subprocess.CompletedProcess[Any]
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        else:
            result = subprocess.run(cmd, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Exit code: {e.returncode}")
        if capture and e.stderr:
            print(f"Error: {e.stderr}")
        raise


def setup_claude(args: Any) -> bool:
    """Set up HtmlGraph for Claude Code."""
    print("🔧 Setting up HtmlGraph for Claude Code...")
    print()

    # Check if claude CLI exists
    if not check_command_exists("claude"):
        print("❌ Claude Code CLI not found")
        print("   Install from: https://claude.com/download")
        return False

    print("✅ Claude Code CLI found")

    # Check if marketplace is configured
    print("\n📦 Checking marketplace configuration...")

    # Get project root (where .htmlgraph might be)
    project_root = Path.cwd()
    marketplace_file = project_root / ".claude-plugin" / "marketplace.json"

    if marketplace_file.exists():
        print(f"✅ Marketplace configured at {marketplace_file}")
    else:
        print("⚠️  No local marketplace found")
        print("   If you're developing HtmlGraph, you should be in the repo root")
        print("   Otherwise, the plugin is available from the official marketplace")

    # Check if plugin is installed
    print("\n📋 Checking installed plugins...")
    try:
        result = run_command(["claude", "plugin", "list"], capture=True)
        if "htmlgraph" in result.stdout:
            print("✅ HtmlGraph plugin already installed")

            # Try to get version
            if "@" in result.stdout:
                version_line = [
                    line for line in result.stdout.split("\n") if "htmlgraph" in line
                ]
                if version_line:
                    print(f"   {version_line[0].strip()}")
        else:
            print("⚠️  HtmlGraph plugin not installed")
            print("\n📥 Install the plugin:")

            if marketplace_file.exists():
                print("   From local marketplace:")
                print("   1. /plugin marketplace add .")
                print("   2. /plugin install htmlgraph@htmlgraph-dev")
            else:
                print("   From official marketplace:")
                print("   /plugin install htmlgraph")
    except Exception as e:
        print(f"⚠️  Could not check plugins: {e}")

    print("\n✅ Claude Code setup complete!")
    print("\n📚 Next steps:")
    print("   1. Restart Claude Code if plugin was just installed")
    print("   2. Run: htmlgraph init --install-hooks")
    print("   3. Start coding - tracking is automatic!")
    return True


def setup_codex(args: Any) -> bool:
    """Set up HtmlGraph for Codex CLI."""
    print("🔧 Setting up HtmlGraph for Codex CLI...")
    print()

    # Check if codex CLI exists
    if not check_command_exists("codex"):
        print("❌ Codex CLI not found")
        print("   Install with: npm install -g @openai/codex")
        return False

    print("✅ Codex CLI found")

    # Check if skills are enabled
    print("\n🎯 Checking if skills are enabled...")
    print("   Run: codex --enable skills")
    print("   (This only needs to be done once)")

    # Find or create skills directory
    home = Path.home()
    codex_dir = home / ".codex"
    skills_dir = codex_dir / "skills"
    htmlgraph_skill_dir = skills_dir / "htmlgraph-tracker"

    print(f"\n📁 Skills directory: {skills_dir}")

    if not skills_dir.exists():
        print("⚠️  Skills directory doesn't exist yet")
        print("   It will be created when you enable skills")
    else:
        print("✅ Skills directory exists")

    # Check if skill is already installed
    if htmlgraph_skill_dir.exists():
        print(f"\n✅ HtmlGraph skill already installed at {htmlgraph_skill_dir}")

        # Check if SKILL.md exists
        skill_md = htmlgraph_skill_dir / "SKILL.md"
        if skill_md.exists():
            print("✅ SKILL.md found")
        else:
            print("⚠️  SKILL.md not found - skill may be incomplete")
    else:
        print("\n⚠️  HtmlGraph skill not installed")
        print("\n📥 Installation options:")

        # Check if we're in the HtmlGraph repo
        repo_skill = Path.cwd() / "packages" / "codex-skill"
        if repo_skill.exists():
            print("\n   Option 1: Link from this repo (recommended for development):")
            print(f"   ln -s {repo_skill.absolute()} {htmlgraph_skill_dir}")

            if args.auto_install:
                print("\n   Auto-installing...")
                skills_dir.mkdir(parents=True, exist_ok=True)
                try:
                    if htmlgraph_skill_dir.exists():
                        htmlgraph_skill_dir.unlink()
                    htmlgraph_skill_dir.symlink_to(repo_skill.absolute())
                    print(f"   ✅ Skill linked to {htmlgraph_skill_dir}")
                except Exception as e:
                    print(f"   ❌ Failed to link skill: {e}")

        print("\n   Option 2: Copy from GitHub:")
        print("   git clone https://github.com/shakestzd/htmlgraph.git")
        print(f"   cp -r htmlgraph/packages/codex-skill {htmlgraph_skill_dir}")

        print("\n   Option 3: Download manually:")
        print(
            "   https://github.com/shakestzd/htmlgraph/tree/main/packages/codex-skill"
        )

    # Check MCP configuration
    print("\n🔌 Checking MCP configuration...")
    codex_config = codex_dir / "config.toml"

    if codex_config.exists():
        print(f"✅ Codex config found at {codex_config}")
        print("   MCP servers can be configured in this file")
        print("   Run: codex mcp serve")
    else:
        print("⚠️  No Codex config found yet")
        print("   It will be created when you run Codex for the first time")

    print("\n✅ Codex CLI setup complete!")
    print("\n📚 Next steps:")
    print("   1. Enable skills: codex --enable skills")
    print("   2. Install the skill (see options above)")
    print("   3. Run: htmlgraph init --install-hooks")
    print("   4. Start Codex - skill will auto-activate!")
    return True


def setup_gemini(args: Any) -> bool:
    """Set up HtmlGraph for Gemini CLI."""
    print("🔧 Setting up HtmlGraph for Gemini CLI...")
    print()

    # Check if gemini CLI exists
    if not check_command_exists("gemini"):
        print("❌ Gemini CLI not found")
        print("   Install with: npm install -g @google/generative-ai-cli")
        return False

    print("✅ Gemini CLI found")

    # Check for extensions
    print("\n🎯 Checking for HtmlGraph extension...")

    try:
        result = run_command(
            ["gemini", "extensions", "list"], capture=True, check=False
        )
        if result.returncode == 0 and "htmlgraph" in result.stdout.lower():
            print("✅ HtmlGraph extension already installed")
        else:
            print("⚠️  HtmlGraph extension not installed")
            print("\n📥 Installation options:")

            # Check if we're in the HtmlGraph repo
            repo_extension = Path.cwd() / "packages" / "gemini-extension"
            if repo_extension.exists():
                print("\n   Option 1: Install from this repo:")
                print(f"   gemini extensions install {repo_extension.absolute()}")

                if args.auto_install:
                    print("\n   Auto-installing...")
                    try:
                        run_command(
                            [
                                "gemini",
                                "extensions",
                                "install",
                                str(repo_extension.absolute()),
                            ]
                        )
                        print("   ✅ Extension installed")
                    except Exception as e:
                        print(f"   ❌ Failed to install extension: {e}")

            print("\n   Option 2: Install from GitHub:")
            print(
                "   gemini extensions install https://github.com/shakestzd/htmlgraph/tree/main/packages/gemini-extension"
            )

            print("\n   Option 3: Create manually:")
            print("   gemini extensions create htmlgraph-tracker")
    except Exception as e:
        print(f"⚠️  Could not check extensions: {e}")

    # Check hooks capability
    print("\n🎉 Good news: Gemini CLI supports hooks!")
    print("   The HtmlGraph extension includes automatic session tracking:")
    print("   - SessionStart hook → Auto-start session")
    print("   - AfterTool hook → Track all tool usage")
    print("   - SessionEnd hook → Auto-finalize session")
    print("   Just like Claude Code - no manual session management needed!")

    print("\n✅ Gemini CLI setup complete!")
    print("\n📚 Next steps:")
    print("   1. Install the extension (see options above)")
    print("   2. Run: htmlgraph init --install-hooks")
    print("   3. Start Gemini - tracking is automatic!")
    return True


def setup_all(args: Any) -> bool:
    """Set up HtmlGraph for all supported platforms."""
    print("🚀 Setting up HtmlGraph for all supported platforms...")
    print("=" * 60)
    print()

    results = {}

    # Claude Code
    print("1️⃣  CLAUDE CODE")
    print("-" * 60)
    results["claude"] = setup_claude(args)
    print()
    print()

    # Codex CLI
    print("2️⃣  CODEX CLI")
    print("-" * 60)
    results["codex"] = setup_codex(args)
    print()
    print()

    # Gemini CLI
    print("3️⃣  GEMINI CLI")
    print("-" * 60)
    results["gemini"] = setup_gemini(args)
    print()
    print()

    # Summary
    print("=" * 60)
    print("📊 SETUP SUMMARY")
    print("=" * 60)
    for platform, success in results.items():
        status = "✅" if success else "⚠️ "
        print(
            f"{status} {platform.upper()}: {'Ready' if success else 'Needs attention'}"
        )
    print()

    return all(results.values())
