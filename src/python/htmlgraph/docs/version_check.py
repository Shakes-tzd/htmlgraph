"""
Version checking and interactive upgrade workflows.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from rich.prompt import Prompt

from htmlgraph.docs.docs_version import get_current_doc_version, is_compatible
from htmlgraph.docs.metadata import DocsMetadata
from htmlgraph.docs.migrations import get_migration

if TYPE_CHECKING:
    from htmlgraph.docs.migrations import MigrationScript


def check_docs_version(htmlgraph_dir: Path) -> tuple[bool, str | None]:
    """Check if docs version is compatible.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory

    Returns:
        Tuple of (is_compatible, message)
        - is_compatible: True if compatible
        - message: Optional warning/error message
    """
    metadata = DocsMetadata.load(htmlgraph_dir)
    current_version = get_current_doc_version()

    if metadata.schema_version == current_version:
        return True, None

    if is_compatible(metadata.schema_version, current_version):
        return (
            True,
            f"⚠️  Docs version {metadata.schema_version} is supported but outdated (current: {current_version})",
        )

    return (
        False,
        f"❌ Docs version {metadata.schema_version} is incompatible with package (requires: {current_version})",
    )


def upgrade_docs_interactive(htmlgraph_dir: Path) -> None:
    """Interactive upgrade workflow with user prompts.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory
    """
    metadata = DocsMetadata.load(htmlgraph_dir)
    current_version = get_current_doc_version()

    if metadata.schema_version == current_version:
        print("✅ Docs are up to date")
        return

    # Get migration script
    migration = get_migration(metadata.schema_version, current_version)
    if not migration:
        print(
            f"❌ No migration available from v{metadata.schema_version} to v{current_version}"
        )
        return

    # Show user their options
    print(
        f"""
📋 Documentation Upgrade Available
  Current: v{metadata.schema_version}
  Target:  v{current_version}

  Options:
    1. Auto-migrate (preserves customizations)
    2. Side-by-side (test before committing)
    3. Manual migration (view diff first)
    4. Skip (stay on v{metadata.schema_version})
  """
    )

    choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4"], default="4")

    if choice == "1":
        _auto_migrate(htmlgraph_dir, migration)
    elif choice == "2":
        _side_by_side_migrate(htmlgraph_dir, migration)
    elif choice == "3":
        _show_diff_for_manual(htmlgraph_dir, migration)
    else:
        print("⏭️  Skipping migration")


def _auto_migrate(htmlgraph_dir: Path, migration: "MigrationScript") -> None:  # type: ignore[name-defined]
    """Automatically migrate with backup.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory
        migration: MigrationScript instance
    """
    backup_dir = htmlgraph_dir / ".docs-backups"
    backup_dir.mkdir(exist_ok=True)

    print("🚀 Starting auto-migration...")
    success = migration.migrate(htmlgraph_dir, backup_dir)

    if success:
        print("✅ Migration complete!")
        print(f"📦 Backup saved to {backup_dir}")
    else:
        print("❌ Migration failed. Docs unchanged.")


def _side_by_side_migrate(htmlgraph_dir: Path, migration: "MigrationScript") -> None:  # type: ignore[name-defined]
    """Create side-by-side versions for testing.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory
        migration: MigrationScript instance
    """
    print("📋 Creating side-by-side versions...")
    print("⚠️  Side-by-side migration not yet implemented")
    print("    Use option 1 (auto-migrate) or 3 (manual) instead")


def _show_diff_for_manual(htmlgraph_dir: Path, migration: "MigrationScript") -> None:  # type: ignore[name-defined]
    """Show diff preview for manual migration.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory
        migration: MigrationScript instance
    """
    print("📊 Showing migration preview...")
    print("⚠️  Diff preview not yet implemented")
    print("    Use option 1 (auto-migrate) instead")


def check_version_on_init(htmlgraph_dir: Path, auto_upgrade: bool = False) -> bool:
    """Check version compatibility on SDK initialization.

    Args:
        htmlgraph_dir: Path to .htmlgraph directory
        auto_upgrade: If True, automatically upgrade if safe

    Returns:
        True if compatible or upgraded successfully
    """
    compatible, message = check_docs_version(htmlgraph_dir)

    if compatible and message:
        # Compatible but outdated
        print(message)
        if auto_upgrade:
            upgrade_docs_interactive(htmlgraph_dir)
        return True

    if not compatible:
        print(message)
        print("\nRun `uv run htmlgraph docs upgrade` to migrate.")
        return False

    return True
