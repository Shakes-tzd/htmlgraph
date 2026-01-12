"""
Shared git command classification for hooks.

Provides consistent rules for which git operations are allowed vs require delegation.
Used by both validator.py and orchestrator.py to ensure consistent behavior.
"""

from typing import Literal

GitCommandType = Literal["read", "write", "unknown"]

# Read-only git commands (safe to allow)
GIT_READ_ONLY = {
    "status",
    "log",
    "diff",
    "show",
    "branch",  # When used with -l or --list or no args
    "reflog",
    "ls-files",
    "ls-remote",
    "rev-parse",
    "describe",
    "tag",  # When used without -a/-d or with -l
    "remote",  # When used with -v or show
}

# Write operations (require delegation)
GIT_WRITE_OPS = {
    "add",
    "commit",
    "push",
    "pull",
    "fetch",
    "merge",
    "rebase",
    "cherry-pick",
    "reset",
    "checkout",  # Can modify working tree
    "switch",
    "restore",
    "rm",
    "mv",
    "clean",
    "stash",
}


def classify_git_command(command: str) -> GitCommandType:
    """
    Classify a git command as read, write, or unknown.

    Args:
        command: Full command string (e.g., "git status" or "git add .")

    Returns:
        "read", "write", or "unknown"

    Examples:
        >>> classify_git_command("git status")
        "read"
        >>> classify_git_command("git commit -m 'msg'")
        "write"
        >>> classify_git_command("git log --oneline")
        "read"
        >>> classify_git_command("git add .")
        "write"
    """
    # Strip "git" prefix and get subcommand
    parts = command.strip().split()
    if not parts or parts[0] != "git":
        return "unknown"

    if len(parts) < 2:
        return "unknown"

    subcommand = parts[1]

    # Check write operations first (more critical)
    if subcommand in GIT_WRITE_OPS:
        return "write"

    # Special handling for branch (flag-based classification)
    if subcommand == "branch":
        # branch with -d or -D flags is write, otherwise read
        if len(parts) > 2:
            flags = " ".join(parts[2:])
            if (
                " -d " in flags
                or " -D " in flags
                or flags.startswith("-d ")
                or flags.startswith("-D ")
            ):
                return "write"
        return "read"

    # Special handling for tag (flag-based classification)
    if subcommand == "tag":
        # tag with -a (annotated) or -d (delete) flags is write, otherwise read
        if len(parts) > 2:
            flags = " ".join(parts[2:])
            if (
                " -a " in flags
                or " -d " in flags
                or flags.startswith("-a ")
                or flags.startswith("-d ")
            ):
                return "write"
        return "read"

    # Then check read-only
    if subcommand in GIT_READ_ONLY:
        return "read"

    # Unknown git command
    return "unknown"


def should_allow_git_command(command: str) -> bool:
    """
    Check if a git command should be allowed without delegation.

    Returns:
        True if command is read-only (safe), False if write (delegate)

    Examples:
        >>> should_allow_git_command("git status")
        True
        >>> should_allow_git_command("git commit -m 'msg'")
        False
        >>> should_allow_git_command("git diff HEAD~1")
        True
        >>> should_allow_git_command("git push origin main")
        False
    """
    cmd_type = classify_git_command(command)
    return cmd_type == "read"


def get_git_delegation_reason(command: str) -> str:
    """
    Get delegation reason for git write operations.

    Args:
        command: Git command that requires delegation

    Returns:
        Human-readable reason explaining why delegation is required
    """
    parts = command.strip().split()
    if len(parts) < 2:
        return "Git write operations should be delegated to Skill('.claude-plugin:copilot')"

    subcommand = parts[1]

    if subcommand in ["commit", "add", "push"]:
        return (
            f"Git {subcommand} is a write operation and should be delegated to "
            f"Skill('.claude-plugin:copilot') for proper Git workflow management"
        )
    elif subcommand in ["merge", "rebase", "cherry-pick"]:
        return (
            f"Git {subcommand} is a complex merge operation and should be delegated to "
            f"Skill('.claude-plugin:copilot') for safe execution"
        )
    elif subcommand in ["reset", "checkout", "restore"]:
        return (
            f"Git {subcommand} can modify working tree and should be delegated to "
            f"Skill('.claude-plugin:copilot') for safe execution"
        )
    else:
        return (
            f"Git {subcommand} is a write operation and should be delegated to "
            f"Skill('.claude-plugin:copilot')"
        )
