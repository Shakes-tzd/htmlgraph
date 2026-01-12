#!/usr/bin/env python3
"""
Analyze the impact of orchestrator workflow on session efficiency - Event-based analysis.

Instead of splitting sessions by start date, we analyze individual events by their timestamp.
This gives us a more accurate picture of behavior changes over time.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path

from htmlgraph import SDK

# Timeline: Based on git log, orchestrator enforcement started around Dec 30, 2025
CUTOFF_DATE = datetime(2025, 12, 30, 0, 0, 0)


def analyze_sessions():
    """Analyze all sessions and extract event-level data."""
    from bs4 import BeautifulSoup

    sessions_dir = Path(".htmlgraph/sessions")
    session_files = list(sessions_dir.glob("*.html"))

    all_events = []
    session_stats = []

    for session_file in session_files:
        if "demo" in session_file.name:
            continue

        try:
            with open(session_file) as f:
                html = f.read()

            soup = BeautifulSoup(html, "html.parser")
            article = soup.find("article")
            if not article:
                continue

            session_id = article.get("id", session_file.stem)
            started_at = article.get("data-started-at", "")
            last_activity = article.get("data-last-activity", "")

            # Parse session times
            try:
                session_start = datetime.fromisoformat(
                    started_at.replace("Z", "+00:00")
                )
            except:
                continue

            try:
                session_end = datetime.fromisoformat(
                    last_activity.replace("Z", "+00:00")
                )
            except:
                session_end = session_start

            # Extract events
            activity_log = soup.find("section", {"data-activity-log": True})
            if activity_log:
                event_items = activity_log.find_all("li", {"data-tool": True})

                session_events = []
                for item in event_items:
                    tool = item.get("data-tool")
                    ts = item.get("data-ts")

                    if ts:
                        try:
                            event_time = datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            )
                            # Make timezone-naive for comparison
                            event_time = event_time.replace(tzinfo=None)

                            all_events.append(
                                {
                                    "session": session_id,
                                    "tool": tool,
                                    "timestamp": event_time,
                                    "is_post_orchestrator": event_time >= CUTOFF_DATE,
                                }
                            )
                            session_events.append(
                                {"tool": tool, "timestamp": event_time}
                            )
                        except:
                            pass

                # Session-level stats
                if session_events:
                    session_start_naive = session_start.replace(tzinfo=None)
                    session_end_naive = session_end.replace(tzinfo=None)
                    duration = (
                        session_end_naive - session_start_naive
                    ).total_seconds() / 60

                    # Count features
                    worked_on = soup.find("section", {"data-edge-type": "worked-on"})
                    num_features = len(worked_on.find_all("a")) if worked_on else 0

                    session_stats.append(
                        {
                            "session_id": session_id,
                            "start": session_start_naive,
                            "end": session_end_naive,
                            "duration_minutes": duration,
                            "num_events": len(session_events),
                            "num_features": num_features,
                            "tool_counts": Counter(e["tool"] for e in session_events),
                        }
                    )
        except Exception as e:
            print(f"Error analyzing {session_file.name}: {e}")

    return all_events, session_stats


def calculate_event_stats(events: list[dict], label: str):
    """Calculate statistics for a group of events."""
    if not events:
        return None

    tool_counts = Counter(e["tool"] for e in events)
    total_events = len(events)

    task_count = tool_counts.get("Task", 0)
    bash_count = tool_counts.get("Bash", 0)

    delegation_rate = (task_count / total_events * 100) if total_events > 0 else 0
    direct_exec_rate = (bash_count / total_events * 100) if total_events > 0 else 0

    return {
        "label": label,
        "total_events": total_events,
        "tool_counts": dict(tool_counts),
        "delegation_rate": delegation_rate,
        "direct_exec_rate": direct_exec_rate,
        "task_count": task_count,
        "bash_count": bash_count,
    }


def main():
    """Main analysis function."""
    print("=" * 80)
    print("ORCHESTRATOR IMPACT ANALYSIS (Event-Level)")
    print("=" * 80)
    print(f"\nCutoff Date: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Analyzing individual events by timestamp, not session start date")
    print()

    all_events, session_stats = analyze_sessions()

    print(f"Total events analyzed: {len(all_events)}")
    print(f"Total sessions: {len(session_stats)}")
    print()

    # Split events by timeline
    pre_events = [e for e in all_events if not e["is_post_orchestrator"]]
    post_events = [e for e in all_events if e["is_post_orchestrator"]]

    print(f"Pre-orchestrator events (< Dec 30): {len(pre_events)}")
    print(f"Post-orchestrator events (>= Dec 30): {len(post_events)}")
    print()

    # Calculate statistics
    pre_stats = calculate_event_stats(pre_events, "Pre-Orchestrator")
    post_stats = calculate_event_stats(post_events, "Post-Orchestrator")

    if not pre_stats or not post_stats:
        print("⚠️  Insufficient data for comparison")
        if not post_stats:
            print(
                "\nNo post-orchestrator events found. The orchestrator workflow may not have"
            )
            print(
                "generated enough activity yet, or the cutoff date may be too recent."
            )
        return

    # Print results
    print("=" * 80)
    print("PRE-ORCHESTRATOR EVENTS (< Dec 30, 2025)")
    print("=" * 80)
    print_event_stats(pre_stats)

    print("\n" + "=" * 80)
    print("POST-ORCHESTRATOR EVENTS (>= Dec 30, 2025)")
    print("=" * 80)
    print_event_stats(post_stats)

    print("\n" + "=" * 80)
    print("COMPARISON & IMPACT ANALYSIS")
    print("=" * 80)
    print_comparison(pre_stats, post_stats)

    # Analyze session-level patterns
    print("\n" + "=" * 80)
    print("SESSION-LEVEL PATTERNS")
    print("=" * 80)
    analyze_session_patterns(session_stats)

    # Save results
    sdk = SDK(agent="analyzer")
    findings = format_findings(
        pre_stats, post_stats, session_stats, pre_events, post_events
    )

    spike = (
        sdk.spikes.create("Orchestrator Impact Analysis - Event Level")
        .set_findings(findings)
        .save()
    )

    print(f"\n✅ Results saved to spike: {spike.id}")
    print(f"   View at: .htmlgraph/spikes/{spike.id}.html")


def print_event_stats(stats: dict):
    """Print statistics for event groups."""
    print(f"\nTotal Events: {stats['total_events']}")
    print("\nDelegation Metrics:")
    print(f"  Task calls: {stats['task_count']} ({stats['delegation_rate']:.1f}%)")
    print(f"  Bash calls: {stats['bash_count']} ({stats['direct_exec_rate']:.1f}%)")

    print("\nTop Tools:")
    sorted_tools = sorted(
        stats["tool_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for tool, count in sorted_tools[:15]:
        pct = count / stats["total_events"] * 100
        print(f"  {tool:20s}: {count:4d} ({pct:5.1f}%)")


def print_comparison(pre: dict, post: dict):
    """Print comparison between pre and post."""
    print("\nTotal Events:")
    print(f"  Pre:  {pre['total_events']}")
    print(f"  Post: {post['total_events']}")
    change = (post["total_events"] - pre["total_events"]) / pre["total_events"] * 100
    print(f"  Change: {change:+.1f}%")

    print("\nDelegation Rate (Task tool):")
    print(f"  Pre:  {pre['delegation_rate']:.1f}% ({pre['task_count']} calls)")
    print(f"  Post: {post['delegation_rate']:.1f}% ({post['task_count']} calls)")
    change = post["delegation_rate"] - pre["delegation_rate"]
    print(f"  Change: {change:+.1f} percentage points")

    print("\nDirect Execution Rate (Bash tool):")
    print(f"  Pre:  {pre['direct_exec_rate']:.1f}% ({pre['bash_count']} calls)")
    print(f"  Post: {post['direct_exec_rate']:.1f}% ({post['bash_count']} calls)")
    change = post["direct_exec_rate"] - pre["direct_exec_rate"]
    print(f"  Change: {change:+.1f} percentage points")

    # Efficiency ratio
    pre_ratio = pre["task_count"] / pre["bash_count"] if pre["bash_count"] > 0 else 0
    post_ratio = (
        post["task_count"] / post["bash_count"] if post["bash_count"] > 0 else 0
    )
    print("\nTask:Bash Ratio (higher = more delegation):")
    print(f"  Pre:  {pre_ratio:.2f}:1")
    print(f"  Post: {post_ratio:.2f}:1")
    if pre_ratio > 0:
        ratio_change = (post_ratio - pre_ratio) / pre_ratio * 100
        print(f"  Change: {ratio_change:+.1f}%")


def analyze_session_patterns(session_stats: list[dict]):
    """Analyze session-level patterns."""
    if not session_stats:
        print("No session data available")
        return

    # Group sessions by pre/post
    pre_sessions = [s for s in session_stats if s["end"] < CUTOFF_DATE]
    post_sessions = [s for s in session_stats if s["start"] >= CUTOFF_DATE]
    mixed_sessions = [s for s in session_stats if s["start"] < CUTOFF_DATE <= s["end"]]

    print("\nSession Timeline Distribution:")
    print(f"  Purely pre-orchestrator: {len(pre_sessions)}")
    print(f"  Purely post-orchestrator: {len(post_sessions)}")
    print(f"  Spans cutoff date: {len(mixed_sessions)}")

    if mixed_sessions:
        print("\nSessions that span the cutoff date:")
        for s in mixed_sessions:
            print(
                f"  {s['session_id']}: {s['start'].strftime('%Y-%m-%d %H:%M')} → "
                f"{s['end'].strftime('%Y-%m-%d %H:%M')} ({s['num_events']} events)"
            )


def format_findings(pre_stats, post_stats, session_stats, pre_events, post_events):
    """Format findings for HtmlGraph spike."""

    def pct_change(pre_val, post_val):
        if pre_val == 0:
            return float("inf") if post_val > 0 else 0
        return ((post_val - pre_val) / pre_val) * 100

    findings = f"""
## Analysis Method

This analysis uses **event-level timestamps** rather than session start dates to classify tool usage as pre or post-orchestrator. This provides a more accurate picture of behavioral changes.

**Timeline:**
- **Cutoff Date**: December 30, 2025 00:00:00
- **Pre-orchestrator**: Events with timestamp < Dec 30, 2025
- **Post-orchestrator**: Events with timestamp >= Dec 30, 2025

## Event-Level Analysis

### Pre-Orchestrator Events (< Dec 30, 2025)

**Total Events**: {pre_stats["total_events"]}

**Delegation Metrics:**
- Task calls: {pre_stats["task_count"]} ({pre_stats["delegation_rate"]:.1f}%)
- Bash calls: {pre_stats["bash_count"]} ({pre_stats["direct_exec_rate"]:.1f}%)
- Task:Bash ratio: {pre_stats["task_count"] / pre_stats["bash_count"] if pre_stats["bash_count"] > 0 else 0:.2f}:1

**Top Tools:**
"""

    sorted_tools = sorted(
        pre_stats["tool_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for tool, count in sorted_tools[:10]:
        pct = count / pre_stats["total_events"] * 100
        findings += f"\n- {tool}: {count} ({pct:.1f}%)"

    findings += f"""

### Post-Orchestrator Events (>= Dec 30, 2025)

**Total Events**: {post_stats["total_events"]}

**Delegation Metrics:**
- Task calls: {post_stats["task_count"]} ({post_stats["delegation_rate"]:.1f}%)
- Bash calls: {post_stats["bash_count"]} ({post_stats["direct_exec_rate"]:.1f}%)
- Task:Bash ratio: {post_stats["task_count"] / post_stats["bash_count"] if post_stats["bash_count"] > 0 else 0:.2f}:1

**Top Tools:**
"""

    sorted_tools = sorted(
        post_stats["tool_counts"].items(), key=lambda x: x[1], reverse=True
    )
    for tool, count in sorted_tools[:10]:
        pct = count / post_stats["total_events"] * 100
        findings += f"\n- {tool}: {count} ({pct:.1f}%)"

    # Calculate changes
    delegation_change = post_stats["delegation_rate"] - pre_stats["delegation_rate"]
    direct_exec_change = post_stats["direct_exec_rate"] - pre_stats["direct_exec_rate"]

    pre_ratio = (
        pre_stats["task_count"] / pre_stats["bash_count"]
        if pre_stats["bash_count"] > 0
        else 0
    )
    post_ratio = (
        post_stats["task_count"] / post_stats["bash_count"]
        if post_stats["bash_count"] > 0
        else 0
    )
    ratio_change = ((post_ratio - pre_ratio) / pre_ratio * 100) if pre_ratio > 0 else 0

    findings += f"""

## Impact Analysis

### Key Findings

**1. Delegation Rate Change:**
- Pre: {pre_stats["delegation_rate"]:.1f}%
- Post: {post_stats["delegation_rate"]:.1f}%
- Change: {delegation_change:+.1f} percentage points
- **Impact**: {"✅ Increased delegation as intended" if delegation_change > 2 else "⚠️  Limited change in delegation behavior"}

**2. Direct Execution Rate Change:**
- Pre: {pre_stats["direct_exec_rate"]:.1f}%
- Post: {post_stats["direct_exec_rate"]:.1f}%
- Change: {direct_exec_change:+.1f} percentage points
- **Impact**: {"✅ Reduced direct execution as intended" if direct_exec_change < -2 else "⚠️  Direct execution rate similar"}

**3. Task:Bash Ratio Change:**
- Pre: {pre_ratio:.2f}:1
- Post: {post_ratio:.2f}:1
- Change: {ratio_change:+.1f}%
- **Impact**: {"✅ Significant improvement in delegation ratio" if ratio_change > 20 else "⚠️  Limited improvement in delegation ratio"}

### Session Statistics

**Total Sessions Analyzed**: {len(session_stats)}
**Pre-orchestrator Only**: {len([s for s in session_stats if s["end"] < CUTOFF_DATE])}
**Post-orchestrator Only**: {len([s for s in session_stats if s["start"] >= CUTOFF_DATE])}
**Spans Cutoff**: {len([s for s in session_stats if s["start"] < CUTOFF_DATE <= s["end"]])}

### Conclusions

{generate_conclusions_v2(pre_stats, post_stats, pre_ratio, post_ratio)}

## Raw Event Timeline
"""

    # Add timeline of events around cutoff
    events_near_cutoff = sorted(
        [e for e in pre_events[-20:]] + [e for e in post_events[:20]],
        key=lambda e: e["timestamp"],
    )

    findings += "\n\n**Events around cutoff date (Dec 30, 2025):**\n"
    for event in events_near_cutoff:
        marker = "📍 PRE " if not event["is_post_orchestrator"] else "📍 POST"
        findings += f"\n- {marker} | {event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {event['tool']} | {event['session']}"

    return findings


def generate_conclusions_v2(pre_stats, post_stats, pre_ratio, post_ratio):
    """Generate conclusions based on event-level data."""
    conclusions = []

    # Delegation change
    delegation_change = post_stats["delegation_rate"] - pre_stats["delegation_rate"]
    if delegation_change > 5:
        conclusions.append(
            f"✅ **Delegation Adopted**: {delegation_change:.1f} percentage point increase in Task usage shows successful orchestrator adoption"
        )
    elif delegation_change > 0:
        conclusions.append(
            f"⚠️  **Modest Delegation Increase**: {delegation_change:.1f} percentage point increase suggests partial adoption"
        )
    else:
        conclusions.append(
            f"❌ **No Delegation Increase**: {abs(delegation_change):.1f} percentage point decrease suggests orchestrator not being followed"
        )

    # Direct execution change
    exec_change = post_stats["direct_exec_rate"] - pre_stats["direct_exec_rate"]
    if exec_change < -5:
        conclusions.append(
            f"✅ **Reduced Direct Execution**: {abs(exec_change):.1f} percentage point reduction in Bash usage"
        )
    elif exec_change < 0:
        conclusions.append(
            f"⚠️  **Modest Reduction**: {abs(exec_change):.1f} percentage point reduction in Bash usage"
        )
    else:
        conclusions.append(
            f"❌ **Increased Direct Execution**: {exec_change:.1f} percentage point increase in Bash usage"
        )

    # Ratio change
    ratio_change = ((post_ratio - pre_ratio) / pre_ratio * 100) if pre_ratio > 0 else 0
    if ratio_change > 50:
        conclusions.append(
            f"✅ **Strong Shift to Delegation**: Task:Bash ratio improved by {ratio_change:.0f}%"
        )
    elif ratio_change > 20:
        conclusions.append(
            f"⚠️  **Moderate Shift**: Task:Bash ratio improved by {ratio_change:.0f}%"
        )
    elif ratio_change < 0:
        conclusions.append(
            f"❌ **Regression**: Task:Bash ratio declined by {abs(ratio_change):.0f}%"
        )

    # Sample size consideration
    if post_stats["total_events"] < 50:
        conclusions.append(
            f"⚠️  **Limited Data**: Only {post_stats['total_events']} post-orchestrator events may not be statistically significant"
        )

    return "\n".join(f"{i + 1}. {c}" for i, c in enumerate(conclusions))


if __name__ == "__main__":
    main()
