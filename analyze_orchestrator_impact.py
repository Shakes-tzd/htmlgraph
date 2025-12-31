#!/usr/bin/env python3
"""
Analyze the impact of orchestrator workflow on session efficiency.

Compares sessions before and after orchestrator enforcement was enabled.
Timeline: Pre-orchestrator (< Dec 30, 2025) vs Post-orchestrator (>= Dec 30, 2025)
"""

import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from htmlgraph import SDK

# Timeline: Based on git log, orchestrator enforcement started around Dec 30, 2025
CUTOFF_DATE = datetime(2025, 12, 30, 0, 0, 0)


def parse_session_timestamp(session_id: str) -> datetime:
    """Extract timestamp from session ID (format: session-YYYYMMDD-HHMMSS)."""
    try:
        # Format: session-20251230-143022
        if session_id.startswith("session-"):
            parts = session_id.split("-")
            if len(parts) >= 3:
                date_str = parts[1]  # YYYYMMDD
                time_str = parts[2] if len(parts) > 2 else "000000"  # HHMMSS

                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[0:2]) if len(time_str) >= 2 else 0
                minute = int(time_str[2:4]) if len(time_str) >= 4 else 0
                second = int(time_str[4:6]) if len(time_str) >= 6 else 0

                return datetime(year, month, day, hour, minute, second)
    except Exception as e:
        print(f"Error parsing timestamp from {session_id}: {e}")

    # Fallback: use file modification time
    return None


def analyze_session(session_file: Path) -> dict[str, Any]:
    """Analyze a single session file."""
    session_id = session_file.stem

    # Parse timestamp
    session_time = parse_session_timestamp(session_id)

    # Read session HTML
    try:
        from bs4 import BeautifulSoup

        with open(session_file) as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # Extract metadata
        article = soup.find("article")
        if not article:
            return None

        # Get timestamps from data attributes
        started_at = article.get("data-started-at", "")
        last_activity = article.get("data-last-activity", "")
        ended_at = article.get("data-ended-at", "")

        # Parse timestamps
        created_dt = None
        updated_dt = None

        if started_at:
            try:
                created_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            except:
                pass

        if last_activity:
            try:
                updated_dt = datetime.fromisoformat(
                    last_activity.replace("Z", "+00:00")
                )
            except:
                pass
        elif ended_at:
            try:
                updated_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            except:
                pass

        # Use created timestamp for timeline classification
        if not session_time and created_dt:
            session_time = created_dt

        # Fallback to parsed ID timestamp
        if not created_dt and session_time:
            created_dt = session_time
        if not updated_dt and session_time:
            updated_dt = session_time

        # Calculate duration
        duration_seconds = (
            (updated_dt - created_dt).total_seconds()
            if created_dt and updated_dt
            else 0
        )

        # Count events - look for activity log
        activity_section = soup.find("section", {"data-activity-log": True})
        events = []
        if activity_section:
            event_items = activity_section.find_all("li", {"data-tool": True})
            events = [
                {"type": item.get("data-tool"), "timestamp": item.get("data-ts")}
                for item in event_items
            ]

        # Also check event count from data attribute
        event_count_attr = article.get("data-event-count", "")
        if event_count_attr and not events:
            # Use the count from attribute if we couldn't parse events
            try:
                num_events = int(event_count_attr)
                events = [
                    {"type": "unknown", "timestamp": None} for _ in range(num_events)
                ]
            except:
                pass

        # Count tool usage
        tool_counts = Counter(event["type"] for event in events)

        # Count features - look for worked-on section
        worked_on_section = soup.find("section", {"data-edge-type": "worked-on"})
        num_features = 0
        if worked_on_section:
            feature_links = worked_on_section.find_all("a")
            num_features = len(feature_links)

        return {
            "session_id": session_id,
            "timestamp": session_time,
            "created": created_dt,
            "updated": updated_dt,
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_seconds / 60,
            "total_events": len(events),
            "tool_counts": dict(tool_counts),
            "num_features": num_features,
            "is_pre_orchestrator": session_time < CUTOFF_DATE if session_time else None,
        }

    except Exception as e:
        print(f"Error analyzing {session_id}: {e}")
        return None


def calculate_stats(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate statistics for a group of sessions."""
    if not sessions:
        return {}

    # Collect metrics
    total_events = [s["total_events"] for s in sessions]
    durations = [s["duration_minutes"] for s in sessions if s["duration_minutes"] > 0]
    num_features = [s["num_features"] for s in sessions]

    # Aggregate tool counts
    all_tools = Counter()
    for s in sessions:
        all_tools.update(s["tool_counts"])

    # Calculate task delegation rate
    task_counts = sum(s["tool_counts"].get("Task", 0) for s in sessions)
    bash_counts = sum(s["tool_counts"].get("Bash", 0) for s in sessions)
    total_tool_calls = sum(sum(s["tool_counts"].values()) for s in sessions)

    delegation_rate = (
        (task_counts / total_tool_calls * 100) if total_tool_calls > 0 else 0
    )
    direct_exec_rate = (
        (bash_counts / total_tool_calls * 100) if total_tool_calls > 0 else 0
    )

    return {
        "n": len(sessions),
        "total_events": {
            "mean": statistics.mean(total_events) if total_events else 0,
            "median": statistics.median(total_events) if total_events else 0,
            "stdev": statistics.stdev(total_events) if len(total_events) > 1 else 0,
            "min": min(total_events) if total_events else 0,
            "max": max(total_events) if total_events else 0,
        },
        "duration_minutes": {
            "mean": statistics.mean(durations) if durations else 0,
            "median": statistics.median(durations) if durations else 0,
            "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
        },
        "num_features": {
            "mean": statistics.mean(num_features) if num_features else 0,
            "median": statistics.median(num_features) if num_features else 0,
            "stdev": statistics.stdev(num_features) if len(num_features) > 1 else 0,
        },
        "tool_counts": dict(all_tools),
        "delegation_rate": delegation_rate,
        "direct_exec_rate": direct_exec_rate,
        "total_tool_calls": total_tool_calls,
    }


def main():
    """Main analysis function."""
    print("=" * 80)
    print("ORCHESTRATOR IMPACT ANALYSIS")
    print("=" * 80)
    print(f"\nCutoff Date: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Pre-orchestrator: Before Dec 30, 2025")
    print("Post-orchestrator: On or after Dec 30, 2025")
    print()

    # Find all session files (both formats)
    sessions_dir = Path(".htmlgraph/sessions")
    session_files = list(sessions_dir.glob("sess*.html")) + list(
        sessions_dir.glob("session-*.html")
    )

    print(f"Found {len(session_files)} total session files\n")

    # Analyze all sessions
    all_sessions = []
    for session_file in session_files:
        result = analyze_session(session_file)
        if result and result["timestamp"]:
            all_sessions.append(result)

    # Split into pre and post
    pre_sessions = [s for s in all_sessions if s["is_pre_orchestrator"]]
    post_sessions = [s for s in all_sessions if not s["is_pre_orchestrator"]]

    print(f"Sessions analyzed: {len(all_sessions)}")
    print(f"  Pre-orchestrator: {len(pre_sessions)}")
    print(f"  Post-orchestrator: {len(post_sessions)}")
    print()

    # Calculate statistics
    pre_stats = calculate_stats(pre_sessions)
    post_stats = calculate_stats(post_sessions)

    # Print results
    print("=" * 80)
    print("PRE-ORCHESTRATOR SESSIONS (< Dec 30, 2025)")
    print("=" * 80)
    print_stats(pre_stats)

    print("\n" + "=" * 80)
    print("POST-ORCHESTRATOR SESSIONS (>= Dec 30, 2025)")
    print("=" * 80)
    print_stats(post_stats)

    print("\n" + "=" * 80)
    print("COMPARISON & IMPACT ANALYSIS")
    print("=" * 80)
    print_comparison(pre_stats, post_stats)

    # Save results
    sdk = SDK(agent="analyzer")
    findings = format_findings(pre_stats, post_stats, pre_sessions, post_sessions)

    spike = (
        sdk.spikes.create("Orchestrator Impact Analysis Results")
        .set_findings(findings)
        .save()
    )

    print(f"\n✅ Results saved to spike: {spike.id}")
    print(f"   View at: .htmlgraph/spikes/{spike.id}.html")


def print_stats(stats: dict[str, Any]):
    """Print statistics for a group of sessions."""
    if not stats:
        print("No data available")
        return

    print(f"\nSample Size: N={stats['n']}")
    print("\nEvents per Session:")
    print(
        f"  Mean: {stats['total_events']['mean']:.1f} ± {stats['total_events']['stdev']:.1f}"
    )
    print(f"  Median: {stats['total_events']['median']:.1f}")
    print(
        f"  Range: {stats['total_events']['min']:.0f} - {stats['total_events']['max']:.0f}"
    )

    print("\nSession Duration (minutes):")
    print(
        f"  Mean: {stats['duration_minutes']['mean']:.1f} ± {stats['duration_minutes']['stdev']:.1f}"
    )
    print(f"  Median: {stats['duration_minutes']['median']:.1f}")
    print(
        f"  Range: {stats['duration_minutes']['min']:.1f} - {stats['duration_minutes']['max']:.1f}"
    )

    print("\nFeatures per Session:")
    print(
        f"  Mean: {stats['num_features']['mean']:.2f} ± {stats['num_features']['stdev']:.2f}"
    )
    print(f"  Median: {stats['num_features']['median']:.1f}")

    print("\nTool Usage Patterns:")
    print(f"  Total tool calls: {stats['total_tool_calls']}")
    print(f"  Delegation rate (Task): {stats['delegation_rate']:.1f}%")
    print(f"  Direct execution rate (Bash): {stats['direct_exec_rate']:.1f}%")

    print("\nTop Tool Calls:")
    sorted_tools = sorted(
        stats["tool_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for tool, count in sorted_tools[:10]:
        pct = (
            (count / stats["total_tool_calls"] * 100)
            if stats["total_tool_calls"] > 0
            else 0
        )
        print(f"  {tool}: {count} ({pct:.1f}%)")


def print_comparison(pre: dict[str, Any], post: dict[str, Any]):
    """Print comparison between pre and post orchestrator."""
    if not pre or not post:
        print("Insufficient data for comparison")
        return

    def pct_change(pre_val, post_val):
        if pre_val == 0:
            return float("inf") if post_val > 0 else 0
        return ((post_val - pre_val) / pre_val) * 100

    print("\nEvents per Session:")
    change = pct_change(pre["total_events"]["mean"], post["total_events"]["mean"])
    print(
        f"  Pre:  {pre['total_events']['mean']:.1f} ± {pre['total_events']['stdev']:.1f}"
    )
    print(
        f"  Post: {post['total_events']['mean']:.1f} ± {post['total_events']['stdev']:.1f}"
    )
    print(f"  Change: {change:+.1f}%")

    print("\nSession Duration (minutes):")
    change = pct_change(
        pre["duration_minutes"]["mean"], post["duration_minutes"]["mean"]
    )
    print(
        f"  Pre:  {pre['duration_minutes']['mean']:.1f} ± {pre['duration_minutes']['stdev']:.1f}"
    )
    print(
        f"  Post: {post['duration_minutes']['mean']:.1f} ± {post['duration_minutes']['stdev']:.1f}"
    )
    print(f"  Change: {change:+.1f}%")

    print("\nDelegation Rate (Task tool usage):")
    change = post["delegation_rate"] - pre["delegation_rate"]
    print(f"  Pre:  {pre['delegation_rate']:.1f}%")
    print(f"  Post: {post['delegation_rate']:.1f}%")
    print(f"  Change: {change:+.1f} percentage points")

    print("\nDirect Execution Rate (Bash tool usage):")
    change = post["direct_exec_rate"] - pre["direct_exec_rate"]
    print(f"  Pre:  {pre['direct_exec_rate']:.1f}%")
    print(f"  Post: {post['direct_exec_rate']:.1f}%")
    print(f"  Change: {change:+.1f} percentage points")

    print("\nFeatures per Session:")
    change = pct_change(pre["num_features"]["mean"], post["num_features"]["mean"])
    print(f"  Pre:  {pre['num_features']['mean']:.2f}")
    print(f"  Post: {post['num_features']['mean']:.2f}")
    print(f"  Change: {change:+.1f}%")


def format_findings(pre_stats, post_stats, pre_sessions, post_sessions):
    """Format findings for HtmlGraph spike."""

    def pct_change(pre_val, post_val):
        if pre_val == 0:
            return float("inf") if post_val > 0 else 0
        return ((post_val - pre_val) / pre_val) * 100

    findings = f"""
## Timeline

**Orchestrator Enforcement Implementation:**
- **Dec 26, 2025**: Initial orchestrator pattern implementation
- **Dec 29, 2025**: Imperative orchestrator guidance system
- **Dec 30, 2025**: HtmlGraph-based delegation system (CUTOFF)
- **Dec 31, 2025**: Validator blocking for orchestrator violations

**Cutoff Date**: December 30, 2025 00:00:00

## Pre-Orchestrator Sessions (N={pre_stats["n"]})

**Events per Session:**
- Mean: {pre_stats["total_events"]["mean"]:.1f} ± {pre_stats["total_events"]["stdev"]:.1f}
- Median: {pre_stats["total_events"]["median"]:.1f}
- Range: {pre_stats["total_events"]["min"]:.0f} - {pre_stats["total_events"]["max"]:.0f}

**Session Duration:**
- Mean: {pre_stats["duration_minutes"]["mean"]:.1f} ± {pre_stats["duration_minutes"]["stdev"]:.1f} minutes
- Median: {pre_stats["duration_minutes"]["median"]:.1f} minutes

**Tool Usage:**
- Total tool calls: {pre_stats["total_tool_calls"]}
- Delegation rate (Task): {pre_stats["delegation_rate"]:.1f}%
- Direct execution rate (Bash): {pre_stats["direct_exec_rate"]:.1f}%

**Features per Session:**
- Mean: {pre_stats["num_features"]["mean"]:.2f} ± {pre_stats["num_features"]["stdev"]:.2f}

## Post-Orchestrator Sessions (N={post_stats["n"]})

**Events per Session:**
- Mean: {post_stats["total_events"]["mean"]:.1f} ± {post_stats["total_events"]["stdev"]:.1f}
- Median: {post_stats["total_events"]["median"]:.1f}
- Range: {post_stats["total_events"]["min"]:.0f} - {post_stats["total_events"]["max"]:.0f}

**Session Duration:**
- Mean: {post_stats["duration_minutes"]["mean"]:.1f} ± {post_stats["duration_minutes"]["stdev"]:.1f} minutes
- Median: {post_stats["duration_minutes"]["median"]:.1f} minutes

**Tool Usage:**
- Total tool calls: {post_stats["total_tool_calls"]}
- Delegation rate (Task): {post_stats["delegation_rate"]:.1f}%
- Direct execution rate (Bash): {post_stats["direct_exec_rate"]:.1f}%

**Features per Session:**
- Mean: {post_stats["num_features"]["mean"]:.2f} ± {post_stats["num_features"]["stdev"]:.2f}

## Impact Analysis

### Key Findings

**1. Events per Session:**
- Change: {pct_change(pre_stats["total_events"]["mean"], post_stats["total_events"]["mean"]):+.1f}%
- {"Decrease in events suggests more efficient workflow" if post_stats["total_events"]["mean"] < pre_stats["total_events"]["mean"] else "Increase in events may indicate more complex tasks or overhead"}

**2. Delegation Rate:**
- Change: {post_stats["delegation_rate"] - pre_stats["delegation_rate"]:+.1f} percentage points
- {"Successful increase in Task tool usage" if post_stats["delegation_rate"] > pre_stats["delegation_rate"] else "No significant change in delegation behavior"}

**3. Direct Execution Rate:**
- Change: {post_stats["direct_exec_rate"] - pre_stats["direct_exec_rate"]:+.1f} percentage points
- {"Reduction in direct Bash calls aligns with orchestrator goals" if post_stats["direct_exec_rate"] < pre_stats["direct_exec_rate"] else "Direct execution rate remains similar"}

**4. Session Duration:**
- Change: {pct_change(pre_stats["duration_minutes"]["mean"], post_stats["duration_minutes"]["mean"]):+.1f}%
- {"Sessions are shorter on average" if post_stats["duration_minutes"]["mean"] < pre_stats["duration_minutes"]["mean"] else "Sessions are longer on average"}

**5. Feature Throughput:**
- Features per session change: {pct_change(pre_stats["num_features"]["mean"], post_stats["num_features"]["mean"]):+.1f}%
- {"More features per session suggests improved productivity" if post_stats["num_features"]["mean"] > pre_stats["num_features"]["mean"] else "Similar feature throughput"}

### Conclusions

{generate_conclusions(pre_stats, post_stats)}

## Raw Data

### Pre-Orchestrator Sessions
"""

    for session in sorted(pre_sessions, key=lambda s: s["timestamp"]):
        findings += f"\n- {session['session_id']}: {session['total_events']} events, {session['duration_minutes']:.1f} min, {session['num_features']} features"

    findings += "\n\n### Post-Orchestrator Sessions\n"

    for session in sorted(post_sessions, key=lambda s: s["timestamp"]):
        findings += f"\n- {session['session_id']}: {session['total_events']} events, {session['duration_minutes']:.1f} min, {session['num_features']} features"

    return findings


def generate_conclusions(pre_stats, post_stats):
    """Generate conclusions based on the data."""
    conclusions = []

    # Events
    events_change = (
        (post_stats["total_events"]["mean"] - pre_stats["total_events"]["mean"])
        / pre_stats["total_events"]["mean"]
        * 100
    )
    if abs(events_change) > 10:
        if events_change < 0:
            conclusions.append(
                f"✅ **Efficiency Gain**: {abs(events_change):.0f}% reduction in events per session suggests more streamlined workflows"
            )
        else:
            conclusions.append(
                f"⚠️ **Overhead Detected**: {events_change:.0f}% increase in events may indicate delegation overhead or more complex tasks"
            )

    # Delegation
    delegation_change = post_stats["delegation_rate"] - pre_stats["delegation_rate"]
    if delegation_change > 5:
        conclusions.append(
            f"✅ **Delegation Adopted**: {delegation_change:.0f} percentage point increase in Task tool usage shows successful orchestrator adoption"
        )
    elif delegation_change < -5:
        conclusions.append(
            f"❌ **Delegation Declined**: {abs(delegation_change):.0f} percentage point decrease suggests orchestrator enforcement not working as intended"
        )

    # Duration
    duration_change = (
        (post_stats["duration_minutes"]["mean"] - pre_stats["duration_minutes"]["mean"])
        / pre_stats["duration_minutes"]["mean"]
        * 100
    )
    if abs(duration_change) > 20:
        if duration_change < 0:
            conclusions.append(
                f"✅ **Faster Sessions**: {abs(duration_change):.0f}% reduction in session duration"
            )
        else:
            conclusions.append(
                f"⚠️ **Longer Sessions**: {duration_change:.0f}% increase in session duration may indicate complexity or learning curve"
            )

    # Features
    features_change = (
        (
            (post_stats["num_features"]["mean"] - pre_stats["num_features"]["mean"])
            / pre_stats["num_features"]["mean"]
            * 100
        )
        if pre_stats["num_features"]["mean"] > 0
        else 0
    )
    if abs(features_change) > 15:
        if features_change > 0:
            conclusions.append(
                f"✅ **Improved Throughput**: {features_change:.0f}% more features per session"
            )
        else:
            conclusions.append(
                f"⚠️ **Reduced Throughput**: {abs(features_change):.0f}% fewer features per session"
            )

    if not conclusions:
        conclusions.append(
            "📊 **Limited Impact**: No significant changes detected in key metrics"
        )

    return "\n".join(f"{i + 1}. {c}" for i, c in enumerate(conclusions))


if __name__ == "__main__":
    main()
