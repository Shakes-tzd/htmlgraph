from __future__ import annotations

"""
Git event logging for HtmlGraph.

These helpers are intended to be invoked from Git hooks and write to the same
append-only JSONL event stream used by HtmlGraph's session/activity tracking.

Design goals:
- Agent-agnostic: works for Codex/Gemini/etc. via Git hooks
- Git-friendly: append-only JSONL under `.htmlgraph/events/`
- Analytics-friendly: schema compatible with EventRecord/AnalyticsIndex
"""


import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from htmlgraph.event_log import EventRecord, JsonlEventLog

if TYPE_CHECKING:
    from htmlgraph.session_manager import SessionManager


def get_git_info() -> dict:
    """
    Get current Git repository information.

    Returns:
        Dictionary with commit hash, branch, author, etc.
        Returns empty dict if not in a Git repo.
    """
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()

        commit_hash_short = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        # Get branch name
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        # Get author info
        author_name = subprocess.check_output(
            ["git", "log", "-1", "--format=%an"], stderr=subprocess.DEVNULL, text=True
        ).strip()

        author_email = subprocess.check_output(
            ["git", "log", "-1", "--format=%ae"], stderr=subprocess.DEVNULL, text=True
        ).strip()

        # Get commit message
        commit_message = subprocess.check_output(
            ["git", "log", "-1", "--format=%B"], stderr=subprocess.DEVNULL, text=True
        ).strip()

        # Get changed files
        files_changed = (
            subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
            .split("\n")
        )
        files_changed = [f for f in files_changed if f]  # Remove empty strings

        # Get stats (insertions/deletions)
        stats = subprocess.check_output(
            ["git", "diff-tree", "--no-commit-id", "--numstat", "-r", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()

        insertions = 0
        deletions = 0
        for line in stats.split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0] != "-" and parts[1] != "-":
                    insertions += int(parts[0])
                    deletions += int(parts[1])

        return {
            "commit_hash": commit_hash,
            "commit_hash_short": commit_hash_short,
            "branch": branch,
            "author_name": author_name,
            "author_email": author_email,
            "commit_message": commit_message,
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        }

    except subprocess.CalledProcessError:
        return {}


def _get_session_manager(graph_dir: str | Path) -> SessionManager | None:
    try:
        from htmlgraph.session_manager import SessionManager

        return SessionManager(graph_dir)
    except Exception:
        return None


def get_active_features(graph_dir: str | Path = ".htmlgraph") -> list[str]:
    """
    Get list of active feature IDs.

    Returns:
        List of feature IDs with status 'in-progress'
    """
    manager = _get_session_manager(graph_dir)
    if not manager:
        return []
    try:
        active = manager.get_active_features()
        return [f.id for f in active]
    except Exception:
        return []


def get_primary_feature_id(graph_dir: str | Path = ".htmlgraph") -> str | None:
    manager = _get_session_manager(graph_dir)
    if not manager:
        return None
    try:
        primary = manager.get_primary_feature()
        return primary.id if primary else None
    except Exception:
        return None


def get_active_session(graph_dir: str | Path = ".htmlgraph") -> Any:
    """
    Get the current active HtmlGraph session.

    Returns:
        Session if active session exists, None otherwise
    """
    manager = _get_session_manager(graph_dir)
    if not manager:
        return None
    try:
        return manager.get_active_session()
    except Exception:
        return None


def parse_feature_refs(message: str) -> list[str]:
    """
    Parse feature IDs from commit message.

    Looks for patterns like:
    - Implements: feat-xyz
    - Fixes: bug-abc
    - [feat-123abc]
    - feat-xyz

    Supports HtmlGraph ID formats:
    - feat-XXXXXXXX (features)
    - feature-XXXXXXXX (legacy features)
    - bug-XXXXXXXX (bugs)
    - spk-XXXXXXXX (spikes)
    - spike-XXXXXXXX (legacy spikes)
    - chr-XXXXXXXX (chores)
    - trk-XXXXXXXX (tracks)

    Args:
        message: Commit message

    Returns:
        List of feature IDs found
    """
    features = []

    # All HtmlGraph ID prefixes (current + legacy)
    id_prefixes = r"(?:feat|feature|bug|spk|spike|chr|chore|trk|track|todo)"

    # Pattern 1: Explicit tags (Implements: feat-xyz)
    pattern1 = rf"(?:Implements|Fixes|Closes|Refs):\s*({id_prefixes}-[\w-]+)"
    features.extend(re.findall(pattern1, message, re.IGNORECASE))

    # Pattern 2: Square brackets [feat-xyz] (common in commit messages)
    pattern2 = rf"\[({id_prefixes}-[\w-]+)\]"
    features.extend(re.findall(pattern2, message, re.IGNORECASE))

    # Pattern 3: Anywhere in message as word boundary
    pattern3 = rf"\b({id_prefixes}-[\w-]+)\b"
    features.extend(re.findall(pattern3, message, re.IGNORECASE))

    # Remove duplicates while preserving order
    seen = set()
    unique_features = []
    for f in features:
        if f not in seen:
            seen.add(f)
            unique_features.append(f)

    return unique_features


def _parse_checkout_from_reflog(
    reflog_action: str | None,
) -> tuple[str | None, str | None]:
    if not reflog_action:
        return None, None
    # Example: "checkout: moving from main to feature/foo"
    m = re.search(r"moving from (?P<frm>.+?) to (?P<to>.+)$", reflog_action)
    if not m:
        return None, None
    return m.group("frm").strip(), m.group("to").strip()


def _append_event(
    *,
    graph_dir: Path,
    session_id: str,
    agent: str,
    event_id: str,
    tool: str,
    summary: str,
    feature_id: str | None,
    file_paths: list[str] | None,
    payload: dict,
    start_commit: str | None,
    continued_from: str | None,
    session_status: str | None,
    now: datetime | None = None,
) -> None:
    # Auto-infer work type from feature_id (Phase 1: Work Type Classification)
    from htmlgraph.work_type_utils import infer_work_type_from_id

    work_type = infer_work_type_from_id(feature_id)

    record = EventRecord(
        event_id=event_id,
        timestamp=now or datetime.now(),
        session_id=session_id,
        agent=agent,
        tool=tool,
        summary=summary,
        success=True,
        feature_id=feature_id,
        drift_score=None,
        start_commit=start_commit,
        continued_from=continued_from,
        work_type=work_type,
        session_status=session_status,
        file_paths=file_paths or [],
        payload=payload,
    )

    # Optional override for custom event file (useful for debugging or routing).
    # If set, write directly to that JSONL path.
    override_path = os.environ.get("HTMLGRAPH_EVENT_FILE")
    if override_path:
        import json

        p = Path(override_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    record.model_dump(mode="json"), ensure_ascii=False, default=str
                )
                + "\n"
            )
        return

    log = JsonlEventLog(graph_dir / "events")
    log.append(record)


def _determine_context(graph_dir: Path, commit_message: str | None = None) -> dict:
    """
    Determine best-effort session + feature context for Git events.

    Returns keys:
      - session_id, agent, start_commit, continued_from, session_status
      - active_features (list[str]), primary_feature_id (str|None)
      - message_features (list[str]), all_features (list[str])
    """
    active_features = get_active_features(graph_dir)
    primary_feature_id = get_primary_feature_id(graph_dir)
    message_features = (
        parse_feature_refs(commit_message or "") if commit_message else []
    )

    all_features: list[str] = []
    for f in active_features + message_features:
        if f and f not in all_features:
            all_features.append(f)

    # Try to find the right session based on feature IDs in commit message
    # This handles multi-agent scenarios where multiple sessions are active
    session = None
    if message_features:
        # If commit mentions specific features, find the session working on them
        manager = _get_session_manager(graph_dir)
        if manager:
            try:
                # Try to find a session that has any of the message features as active
                for feature_id in message_features:
                    # Get the feature to check which agent is working on it
                    try:
                        # Try features graph first
                        feature = manager.features_graph.get(feature_id)
                        if not feature:
                            # Try bugs graph
                            feature = manager.bugs_graph.get(feature_id)

                        if (
                            feature
                            and hasattr(feature, "agent_assigned")
                            and feature.agent_assigned
                        ):
                            # Find active session for this agent
                            session = manager.get_active_session(
                                agent=feature.agent_assigned
                            )
                            if session:
                                break
                    except Exception:
                        pass
            except Exception:
                pass

    # Fallback to any active session if we couldn't match by feature
    if not session:
        session = get_active_session(graph_dir)

    if session:
        return {
            "session_id": session.id,
            "agent": session.agent,
            "start_commit": session.start_commit,
            "continued_from": session.continued_from,
            "session_status": session.status,
            "active_features": active_features,
            "primary_feature_id": primary_feature_id,
            "message_features": message_features,
            "all_features": all_features,
        }

    # No active session: use a stable pseudo-session for Git hook activity.
    return {
        "session_id": "git",
        "agent": "git",
        "start_commit": None,
        "continued_from": None,
        "session_status": None,
        "active_features": active_features,
        "primary_feature_id": primary_feature_id,
        "message_features": message_features,
        "all_features": all_features,
    }


def log_git_commit(graph_dir: str | Path = ".htmlgraph") -> bool:
    """
    Log a Git commit event to HtmlGraph.

    Args:
        graph_dir: HtmlGraph directory (defaults to .htmlgraph)

    Returns:
        True if event was logged successfully, False otherwise
    """
    try:
        graph_dir_path = Path(graph_dir)
        # Get Git info
        git_info = get_git_info()
        if not git_info:
            return False  # Not in a Git repo

        # Best-effort parent list for commit-graph analytics.
        parents: list[str] = []
        try:
            line = subprocess.check_output(
                ["git", "rev-list", "--parents", "-n", "1", git_info["commit_hash"]],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            parts = line.split()
            if len(parts) >= 2:
                parents = parts[1:]
        except Exception:
            parents = []

        ctx = _determine_context(
            graph_dir_path, commit_message=git_info.get("commit_message")
        )
        all_features: list[str] = ctx["all_features"]

        # Create one event per feature (to keep continuity queries simple).
        # If there are no features, write a single un-attributed event.
        feature_ids: list[str | None] = (
            cast(list[str | None], all_features) if all_features else [None]
        )

        subject = (
            (git_info.get("commit_message") or "").strip().splitlines()[0]
            if git_info.get("commit_message")
            else ""
        )
        base_event_id = f"git-commit-{git_info['commit_hash']}"

        for fid in feature_ids:
            event_id = base_event_id if fid is None else f"{base_event_id}-{fid}"
            summary = f"Commit {git_info['commit_hash_short']}: {subject}".strip()
            if fid:
                summary = f"{summary} [{fid}]"

            payload = {
                "type": "GitCommit",
                "commit_hash": git_info["commit_hash"],
                "commit_hash_short": git_info["commit_hash_short"],
                "parents": parents,
                "is_merge": len(parents) > 1,
                "branch": git_info["branch"],
                "author_name": git_info["author_name"],
                "author_email": git_info["author_email"],
                "commit_message": git_info["commit_message"],
                "subject": subject,
                "files_changed": git_info["files_changed"],
                "insertions": git_info["insertions"],
                "deletions": git_info["deletions"],
                "features": all_features,
            }

            _append_event(
                graph_dir=graph_dir_path,
                session_id=ctx["session_id"],
                agent=ctx["agent"],
                event_id=event_id,
                tool="GitCommit",
                summary=summary,
                feature_id=fid,
                file_paths=git_info.get("files_changed") or [],
                payload=payload,
                start_commit=ctx["start_commit"],
                continued_from=ctx["continued_from"],
                session_status=ctx["session_status"],
            )

        return True

    except Exception as e:
        # Never fail - just log error and continue
        try:
            error_log = Path(".htmlgraph/git-hook-errors.log")
            with open(error_log, "a") as f:
                f.write(f"{datetime.now().isoformat()} - Error logging commit: {e}\n")
        except:
            pass

        return False


def log_git_checkout(
    old_head: str | None,
    new_head: str | None,
    flag: str | int | None,
    graph_dir: str | Path = ".htmlgraph",
) -> bool:
    """
    Log a Git checkout/switch event.

    Git passes: post-checkout <old-ref> <new-ref> <flag>
    where flag is "1" for branch checkouts and "0" for file checkouts.
    """
    try:
        graph_dir_path = Path(graph_dir)
        now = datetime.now()

        try:
            flag_int = int(flag) if flag is not None else None
        except Exception:
            flag_int = None

        reflog_action = os.environ.get("GIT_REFLOG_ACTION")
        from_branch, to_branch = _parse_checkout_from_reflog(reflog_action)

        # Always record, but callers can filter later based on flag.
        ctx = _determine_context(graph_dir_path)
        fid = ctx["primary_feature_id"] or (
            ctx["all_features"][0] if ctx["all_features"] else None
        )

        event_id = f"git-checkout-{now.strftime('%Y%m%d%H%M%S')}-{(new_head or 'unknown')[:12]}"
        summary = "Checkout"
        if from_branch and to_branch:
            summary = f"Checkout {from_branch} -> {to_branch}"

        payload = {
            "type": "GitCheckout",
            "old_head": old_head,
            "new_head": new_head,
            "flag": flag_int,
            "reflog_action": reflog_action,
            "from_branch": from_branch,
            "to_branch": to_branch,
        }

        _append_event(
            graph_dir=graph_dir_path,
            session_id=ctx["session_id"],
            agent=ctx["agent"],
            event_id=event_id,
            tool="GitCheckout",
            summary=summary,
            feature_id=fid,
            file_paths=[],
            payload=payload,
            start_commit=ctx["start_commit"],
            continued_from=ctx["continued_from"],
            session_status=ctx["session_status"],
            now=now,
        )
        return True
    except Exception:
        return False


def log_git_merge(
    squash_flag: str | int | None,
    graph_dir: str | Path = ".htmlgraph",
) -> bool:
    """
    Log a successful Git merge event.

    Git passes: post-merge <squash_flag>
    where squash_flag is "1" when a squash merge happened.
    """
    try:
        graph_dir_path = Path(graph_dir)
        now = datetime.now()

        try:
            squash_int = int(squash_flag) if squash_flag is not None else 0
        except Exception:
            squash_int = 0

        # ORIG_HEAD is set by Git to the previous HEAD before merge.
        orig_head = None
        try:
            orig_head = subprocess.check_output(
                ["git", "rev-parse", "ORIG_HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            orig_head = None

        new_head = None
        try:
            new_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            new_head = None

        reflog_action = os.environ.get("GIT_REFLOG_ACTION")

        ctx = _determine_context(graph_dir_path)
        fid = ctx["primary_feature_id"] or (
            ctx["all_features"][0] if ctx["all_features"] else None
        )

        event_id = (
            f"git-merge-{now.strftime('%Y%m%d%H%M%S')}-{(new_head or 'unknown')[:12]}"
        )
        payload = {
            "type": "GitMerge",
            "squash": bool(squash_int),
            "orig_head": orig_head,
            "new_head": new_head,
            "reflog_action": reflog_action,
        }

        _append_event(
            graph_dir=graph_dir_path,
            session_id=ctx["session_id"],
            agent=ctx["agent"],
            event_id=event_id,
            tool="GitMerge",
            summary="Merge",
            feature_id=fid,
            file_paths=[],
            payload=payload,
            start_commit=ctx["start_commit"],
            continued_from=ctx["continued_from"],
            session_status=ctx["session_status"],
            now=now,
        )
        return True
    except Exception:
        return False


def log_git_push(
    remote_name: str | None,
    remote_url: str | None,
    updates_text: str,
    graph_dir: str | Path = ".htmlgraph",
) -> bool:
    """
    Log a Git push event.

    pre-push receives: <remote_name> <remote_url> and stdin lines:
      <local_ref> <local_sha> <remote_ref> <remote_sha>
    """
    try:
        graph_dir_path = Path(graph_dir)
        now = datetime.now()

        updates: list[dict] = []
        for line in (updates_text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            updates.append(
                {
                    "local_ref": parts[0],
                    "local_sha": parts[1],
                    "remote_ref": parts[2],
                    "remote_sha": parts[3],
                }
            )

        ctx = _determine_context(graph_dir_path)
        fid = ctx["primary_feature_id"] or (
            ctx["all_features"][0] if ctx["all_features"] else None
        )

        event_id = f"git-push-{now.strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        payload = {
            "type": "GitPush",
            "remote_name": remote_name,
            "remote_url": remote_url,
            "updates": updates,
        }

        summary = f"Push {remote_name or ''}".strip() or "Push"

        _append_event(
            graph_dir=graph_dir_path,
            session_id=ctx["session_id"],
            agent=ctx["agent"],
            event_id=event_id,
            tool="GitPush",
            summary=summary,
            feature_id=fid,
            file_paths=[],
            payload=payload,
            start_commit=ctx["start_commit"],
            continued_from=ctx["continued_from"],
            session_status=ctx["session_status"],
            now=now,
        )
        return True
    except Exception:
        return False


def main() -> None:
    """CLI entry point for git hook."""
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m htmlgraph.git_events <commit|checkout|merge|push> [args...]"
        )
        sys.exit(1)

    event_type = sys.argv[1]

    if event_type == "commit":
        sys.exit(0 if log_git_commit() else 1)

    if event_type == "checkout":
        old_head = sys.argv[2] if len(sys.argv) > 2 else None
        new_head = sys.argv[3] if len(sys.argv) > 3 else None
        flag = sys.argv[4] if len(sys.argv) > 4 else None
        sys.exit(0 if log_git_checkout(old_head, new_head, flag) else 1)

    if event_type == "merge":
        squash_flag = sys.argv[2] if len(sys.argv) > 2 else None
        sys.exit(0 if log_git_merge(squash_flag) else 1)

    if event_type == "push":
        remote_name = sys.argv[2] if len(sys.argv) > 2 else None
        remote_url = sys.argv[3] if len(sys.argv) > 3 else None
        updates_text = sys.stdin.read()
        sys.exit(0 if log_git_push(remote_name, remote_url, updates_text) else 1)

    print(f"Unknown event type: {event_type}")
    sys.exit(1)


if __name__ == "__main__":
    main()
