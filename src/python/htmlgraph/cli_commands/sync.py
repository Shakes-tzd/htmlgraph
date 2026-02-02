"""
CLI commands for Git-based sync management.

Provides commands to start/stop background sync, trigger manual operations,
and check sync status.
"""

import asyncio
from pathlib import Path

import click

from htmlgraph.sync import GitSyncManager, SyncConfig, SyncStrategy


@click.group()
def sync() -> None:
    """Git-based multi-device sync commands."""
    pass


@sync.command()
@click.option(
    "--push-interval",
    type=int,
    default=300,
    help="Push interval in seconds (default: 300 = 5 min)",
)
@click.option(
    "--pull-interval",
    type=int,
    default=60,
    help="Pull interval in seconds (default: 60 = 1 min)",
)
@click.option(
    "--strategy",
    type=click.Choice(["auto_merge", "abort_on_conflict", "ours", "theirs"]),
    default="auto_merge",
    help="Conflict resolution strategy",
)
@click.option(
    "--repo-root",
    type=click.Path(exists=True),
    default=".",
    help="Git repository root path",
)
def start(
    push_interval: int, pull_interval: int, strategy: str, repo_root: str
) -> None:
    """Start background sync service."""
    config = SyncConfig(
        push_interval_seconds=push_interval,
        pull_interval_seconds=pull_interval,
        conflict_strategy=SyncStrategy(strategy),
    )

    manager = GitSyncManager(repo_root, config)

    click.echo("Starting background sync service...")
    click.echo(f"  Push interval: {push_interval}s")
    click.echo(f"  Pull interval: {pull_interval}s")
    click.echo(f"  Conflict strategy: {strategy}")
    click.echo(f"  Repository: {Path(repo_root).absolute()}")

    try:
        asyncio.run(manager.start_background_sync())
    except KeyboardInterrupt:
        click.echo("\nStopping background sync...")
        asyncio.run(manager.stop_background_sync())


@sync.command()
@click.option(
    "--repo-root",
    type=click.Path(exists=True),
    default=".",
    help="Git repository root path",
)
def push(repo_root: str) -> None:
    """Manually push changes to remote."""
    manager = GitSyncManager(repo_root)

    click.echo("Pushing changes to remote...")

    async def do_push() -> None:
        result = await manager.push(force=True)
        click.echo(f"Status: {result.status.value}")
        click.echo(f"Files changed: {result.files_changed}")
        click.echo(f"Message: {result.message}")
        if result.conflicts:
            click.echo(f"Conflicts: {', '.join(result.conflicts)}")

    asyncio.run(do_push())


@sync.command()
@click.option(
    "--repo-root",
    type=click.Path(exists=True),
    default=".",
    help="Git repository root path",
)
def pull(repo_root: str) -> None:
    """Manually pull changes from remote."""
    manager = GitSyncManager(repo_root)

    click.echo("Pulling changes from remote...")

    async def do_pull() -> None:
        result = await manager.pull(force=True)
        click.echo(f"Status: {result.status.value}")
        click.echo(f"Message: {result.message}")
        if result.conflicts:
            click.echo(f"Conflicts: {', '.join(result.conflicts)}")

    asyncio.run(do_pull())


@sync.command()
@click.option(
    "--repo-root",
    type=click.Path(exists=True),
    default=".",
    help="Git repository root path",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of recent operations to show",
)
def status(repo_root: str, limit: int) -> None:
    """Show sync status and recent history."""
    manager = GitSyncManager(repo_root)

    status_data = manager.get_status()
    history = manager.get_sync_history(limit)

    click.echo("Sync Status:")
    click.echo(f"  Current status: {status_data['status']}")
    click.echo(f"  Last push: {status_data['last_push'] or 'Never'}")
    click.echo(f"  Last pull: {status_data['last_pull'] or 'Never'}")
    click.echo("\nConfiguration:")
    click.echo(f"  Remote: {status_data['config']['remote']}")
    click.echo(f"  Branch: {status_data['config']['branch']}")
    click.echo(f"  Push interval: {status_data['config']['push_interval']}s")
    click.echo(f"  Pull interval: {status_data['config']['pull_interval']}s")
    click.echo(f"  Conflict strategy: {status_data['config']['conflict_strategy']}")

    if history:
        click.echo(f"\nRecent Operations (last {len(history)}):")
        for entry in history:
            click.echo(
                f"  [{entry['operation']}] {entry['status']} - {entry['message']}"
            )


@sync.command()
@click.option(
    "--repo-root",
    type=click.Path(exists=True),
    default=".",
    help="Git repository root path",
)
@click.option(
    "--push-interval",
    type=int,
    help="New push interval in seconds",
)
@click.option(
    "--pull-interval",
    type=int,
    help="New pull interval in seconds",
)
@click.option(
    "--strategy",
    type=click.Choice(["auto_merge", "abort_on_conflict", "ours", "theirs"]),
    help="New conflict resolution strategy",
)
def configure(
    repo_root: str,
    push_interval: int | None,
    pull_interval: int | None,
    strategy: str | None,
) -> None:
    """Update sync configuration."""
    manager = GitSyncManager(repo_root)

    if push_interval:
        manager.config.push_interval_seconds = push_interval
        click.echo(f"Push interval updated to {push_interval}s")

    if pull_interval:
        manager.config.pull_interval_seconds = pull_interval
        click.echo(f"Pull interval updated to {pull_interval}s")

    if strategy:
        manager.config.conflict_strategy = SyncStrategy(strategy)
        click.echo(f"Conflict strategy updated to {strategy}")

    if not any([push_interval, pull_interval, strategy]):
        click.echo("No configuration changes specified")
        click.echo("Use --push-interval, --pull-interval, or --strategy")


if __name__ == "__main__":
    sync()
