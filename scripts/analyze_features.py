#!/usr/bin/env python3
"""
Feature Tracking Data Integrity Analysis

Analyzes all feature files to identify:
1. Status distribution and mismatches
2. Step completion tracking
3. Agent attribution
4. Session linkage
5. Root causes of data drift
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Feature:
    """Represents a feature with all its metadata"""

    id: str
    title: str
    status: str
    steps_total: int
    steps_completed: int
    agent_assigned: str | None
    session_id: str | None
    created_date: str | None
    last_updated: str | None
    has_content: bool


def extract_feature_data(html_file: Path) -> Feature | None:
    """Extract feature metadata from HTML file"""
    try:
        content = html_file.read_text()

        # Extract ID from filename
        feat_id = html_file.stem

        # Extract title
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", content)
        title = title_match.group(1) if title_match else "Unknown"

        # Extract status from data-status attribute
        status_match = re.search(r'data-status=["\']?([^"\'>\s]+)', content)
        status = status_match.group(1) if status_match else "unknown"

        # Count total steps from <li> elements in data-steps section
        steps_section = re.search(
            r"<section data-steps>.*?</section>", content, re.DOTALL
        )
        if steps_section:
            step_list = steps_section.group(0)
            steps_total = len(re.findall(r"<li\s", step_list))
            # Count completed steps (data-completed="true")
            steps_completed = len(re.findall(r'data-completed=["\']?true', step_list))
        else:
            steps_total = 0
            steps_completed = 0

        # Extract agent_assigned from data-agent-assigned attribute
        agent_match = re.search(r'data-agent-assigned=["\']?([^"\'>\s]+)', content)
        agent_assigned = agent_match.group(1) if agent_match else None

        # Extract session ID from data-claimed-by-session attribute
        session_match = re.search(
            r'data-claimed-by-session=["\']?([^"\'>\s]+)', content
        )
        session_id = session_match.group(1) if session_match else None

        # Extract dates
        created_match = re.search(r'data-created=["\']?([^"\'>\s]+)', content)
        created_date = created_match.group(1) if created_match else None

        updated_match = re.search(r'data-updated=["\']?([^"\'>\s]+)', content)
        last_updated = updated_match.group(1) if updated_match else None

        has_content = len(content) > 500  # Has substantive content

        return Feature(
            id=feat_id,
            title=title,
            status=status.lower(),
            steps_total=steps_total,
            steps_completed=steps_completed,
            agent_assigned=agent_assigned,
            session_id=session_id,
            created_date=created_date,
            last_updated=last_updated,
            has_content=has_content,
        )
    except Exception as e:
        print(f"Error parsing {html_file}: {e}")
        return None


def analyze_features() -> tuple[list[Feature], dict]:
    """Load and analyze all features"""
    features_dir = Path("/Users/shakes/DevProjects/htmlgraph/.htmlgraph/features")
    features = []

    for html_file in sorted(features_dir.glob("feat-*.html")):
        feature = extract_feature_data(html_file)
        if feature:
            features.append(feature)

    return features, analyze_data(features)


def analyze_data(features: list[Feature]) -> dict:
    """Analyze feature data for integrity issues"""
    analysis = {
        "total_features": len(features),
        "status_distribution": defaultdict(int),
        "features_by_status": defaultdict(list),
        "agent_attribution": defaultdict(int),
        "untracked_features": [],
        "abandoned_features": [],
        "partially_done": [],
        "status_mismatch": [],
        "untracked_work": [],
    }

    for feature in features:
        # Status distribution
        analysis["status_distribution"][feature.status] += 1
        analysis["features_by_status"][feature.status].append(feature)

        # Agent attribution
        if feature.agent_assigned:
            analysis["agent_attribution"][feature.agent_assigned] += 1
        else:
            analysis["untracked_features"].append(feature)

        # Identify issues
        # Abandoned: todo status, 0 steps
        if (
            feature.status == "todo"
            and feature.steps_completed == 0
            and feature.steps_total > 0
        ):
            analysis["abandoned_features"].append(feature)

        # Partially done: some steps completed but not status=done
        elif 0 < feature.steps_completed < feature.steps_total:
            if feature.status != "done":
                analysis["partially_done"].append(feature)

        # Status mismatch: done status but incomplete steps
        elif (
            feature.status == "done"
            and feature.steps_completed < feature.steps_total
            and feature.steps_total > 0
        ):
            analysis["status_mismatch"].append(feature)

        # Untracked work: no agent but has completed steps
        if not feature.agent_assigned and feature.steps_completed > 0:
            analysis["untracked_work"].append(feature)

    return analysis


def generate_report(features: list[Feature], analysis: dict) -> str:
    """Generate comprehensive analysis report"""
    report = []
    report.append("=" * 80)
    report.append("FEATURE TRACKING DATA INTEGRITY ANALYSIS")
    report.append("=" * 80)
    report.append("")

    # Summary
    report.append("SUMMARY:")
    report.append(f"  Total features: {analysis['total_features']}")
    report.append("")
    report.append("  Status distribution:")
    total_status = sum(analysis["status_distribution"].values())
    for status in sorted(analysis["status_distribution"].keys()):
        count = analysis["status_distribution"][status]
        pct = count / total_status * 100 if total_status > 0 else 0
        report.append(f"    - {status}: {count} ({pct:.1f}%)")
    report.append("")

    # Agent attribution
    report.append("  Agent attribution:")
    untracked_count = len(analysis["untracked_features"])
    tracked_count = analysis["total_features"] - untracked_count
    report.append(
        f"    - Features with agent assigned: {tracked_count} ({tracked_count / analysis['total_features'] * 100:.1f}%)"
    )
    report.append(
        f"    - Features WITHOUT agent assigned: {untracked_count} ({untracked_count / analysis['total_features'] * 100:.1f}%)"
    )
    report.append("")

    if analysis["agent_attribution"]:
        report.append("  Agents who created features:")
        for agent, count in sorted(
            analysis["agent_attribution"].items(), key=lambda x: -x[1]
        ):
            report.append(f"    - {agent}: {count}")
        report.append("")

    # Issue categories
    report.append("ISSUES BY CATEGORY:")
    report.append("")

    # 1. Abandoned Features
    if analysis["abandoned_features"]:
        report.append(f"1. ABANDONED FEATURES ({len(analysis['abandoned_features'])}):")
        report.append(
            "   Created but never worked on (status=todo, 0 steps completed):"
        )
        for feature in sorted(analysis["abandoned_features"], key=lambda f: f.title)[
            :10
        ]:
            agent_info = (
                f"[agent: {feature.agent_assigned}]"
                if feature.agent_assigned
                else "[UNTRACKED]"
            )
            report.append(f"   - {feature.id}: {feature.title} {agent_info}")
        if len(analysis["abandoned_features"]) > 10:
            report.append(f"   ... and {len(analysis['abandoned_features']) - 10} more")
        report.append("")

    # 2. Partially Done
    if analysis["partially_done"]:
        report.append(f"2. PARTIALLY DONE ({len(analysis['partially_done'])}):")
        report.append("   Some steps completed but status not 'done':")
        for feature in sorted(
            analysis["partially_done"],
            key=lambda f: f.steps_completed / max(f.steps_total, 1),
            reverse=True,
        )[:10]:
            pct = (
                feature.steps_completed / feature.steps_total * 100
                if feature.steps_total > 0
                else 0
            )
            report.append(
                f"   - {feature.id}: {feature.steps_completed}/{feature.steps_total} steps ({pct:.0f}%) - status={feature.status}"
            )
            report.append(f"     Title: {feature.title}")
        if len(analysis["partially_done"]) > 10:
            report.append(f"   ... and {len(analysis['partially_done']) - 10} more")
        report.append("")

    # 3. Status Mismatch
    if analysis["status_mismatch"]:
        report.append(
            f"3. STATUS MISMATCH - DONE BUT STEPS INCOMPLETE ({len(analysis['status_mismatch'])}):"
        )
        report.append("   Features marked 'done' but not all steps completed:")
        for feature in sorted(
            analysis["status_mismatch"], key=lambda f: f.steps_total - f.steps_completed
        )[:10]:
            missing = feature.steps_total - feature.steps_completed
            report.append(
                f"   - {feature.id}: {feature.steps_completed}/{feature.steps_total} steps (missing {missing})"
            )
            report.append(f"     Title: {feature.title}")
        if len(analysis["status_mismatch"]) > 10:
            report.append(f"   ... and {len(analysis['status_mismatch']) - 10} more")
        report.append("")

    # 4. Untracked Work
    if analysis["untracked_work"]:
        report.append(f"4. UNTRACKED WORK ({len(analysis['untracked_work'])}):")
        report.append("   Features with completed steps but NO agent assigned:")
        for feature in sorted(
            analysis["untracked_work"], key=lambda f: f.steps_completed, reverse=True
        )[:10]:
            report.append(
                f"   - {feature.id}: {feature.steps_completed}/{feature.steps_total} steps completed - status={feature.status}"
            )
            report.append(f"     Title: {feature.title}")
        if len(analysis["untracked_work"]) > 10:
            report.append(f"   ... and {len(analysis['untracked_work']) - 10} more")
        report.append("")

    # 5. Untracked Features (no agent_assigned at all)
    if analysis["untracked_features"]:
        report.append(
            f"5. UNTRACKED FEATURES (no agent_assigned) ({len(analysis['untracked_features'])}):"
        )
        by_status = defaultdict(list)
        for feature in analysis["untracked_features"]:
            by_status[feature.status].append(feature)

        for status in sorted(by_status.keys()):
            count = len(by_status[status])
            report.append(f"   Status={status}: {count}")
        report.append("")

    # Root Cause Analysis
    report.append("ROOT CAUSE ANALYSIS:")
    report.append("")

    issues_found = [
        analysis["abandoned_features"],
        analysis["partially_done"],
        analysis["status_mismatch"],
        analysis["untracked_work"],
    ]
    total_issues = sum(len(x) for x in issues_found)

    report.append(
        f"Primary Issue: {total_issues} features have data integrity problems ({total_issues / analysis['total_features'] * 100:.1f}%)"
    )
    report.append("")

    if analysis["abandoned_features"]:
        abandoned_pct = (
            len(analysis["abandoned_features"]) / analysis["total_features"] * 100
        )
        report.append(
            f"1. Abandoned Work: {len(analysis['abandoned_features'])} features in 'todo' status with 0 work ({abandoned_pct:.1f}%)"
        )
        report.append("   Possible causes:")
        report.append("   - Features created but deprioritized")
        report.append("   - Features not assigned to anyone")
        report.append("   - Work started in external system, not tracked here")
    report.append("")

    if analysis["partially_done"]:
        report.append(
            f"2. Incomplete Tracking: {len(analysis['partially_done'])} features have partial work but status not updated"
        )
        report.append("   Possible causes:")
        report.append(
            "   - Steps being completed but feature status not promoted to 'done'"
        )
        report.append("   - Feature status not synchronized with step progress")
        report.append("   - No workflow to promote status when steps complete")
    report.append("")

    if analysis["status_mismatch"]:
        report.append(
            f"3. Status Drift: {len(analysis['status_mismatch'])} features marked 'done' but have incomplete steps"
        )
        report.append("   Possible causes:")
        report.append("   - Features marked done without completing all steps")
        report.append("   - Steps added after feature marked done")
        report.append("   - Steps not properly tracked as completed")
    report.append("")

    if analysis["untracked_features"]:
        report.append(
            f"4. Missing Agent Attribution: {len(analysis['untracked_features'])} features have no agent_assigned"
        )
        report.append("   Possible causes:")
        report.append("   - Features created without SDK.create() method")
        report.append("   - Manual HTML creation without agent metadata")
        report.append("   - Agent metadata lost during file migrations")
    report.append("")

    # Repair Strategy
    report.append("REPAIR STRATEGY:")
    report.append("")
    report.append("CATEGORY 1: Auto-Fixable")
    report.append(
        "  1. Partially done features → Mark status as 'in-progress' or 'done' based on step completion %"
    )
    report.append("     Action: For features with >80% steps, auto-promote to 'done'")
    report.append("             For features with >0% steps, set to 'in-progress'")
    report.append("     Count: ~" + str(len(analysis["partially_done"])))
    report.append("")
    report.append("CATEGORY 2: Requires Manual Review")
    report.append("  2. Status mismatch (done but incomplete steps)")
    report.append(
        "     Action: Review each feature - either complete missing steps or downgrade status"
    )
    report.append("     Count: " + str(len(analysis["status_mismatch"])))
    report.append("")
    report.append("  3. Abandoned features (todo, 0 steps)")
    report.append("     Action: Either start work (mark in-progress) or archive")
    report.append("     Count: " + str(len(analysis["abandoned_features"])))
    report.append("")
    report.append("CATEGORY 3: Process Improvement")
    report.append("  4. Add agent attribution to features")
    report.append(
        "     Action: Update feature creation to capture agent from SDK context"
    )
    report.append("     Impact: Prevents future untracked work")
    report.append("")
    report.append("  5. Implement status sync workflow")
    report.append(
        "     Action: Create hook to auto-update feature status when steps change"
    )
    report.append("     Impact: Prevents status drift")
    report.append("")

    report.append("RECOMMENDATIONS:")
    report.append("")
    report.append("IMMEDIATE ACTIONS (Priority 1):")
    report.append("1. Fix status mismatch on 'done' features")
    report.append(
        "   - Review "
        + str(len(analysis["status_mismatch"]))
        + " features marked 'done' with incomplete steps"
    )
    report.append("   - Either complete missing steps or change status")
    report.append("")
    report.append("2. Promote in-progress features")
    report.append(
        "   - " + str(len(analysis["partially_done"])) + " features have partial work"
    )
    report.append("   - Auto-promote >80% complete to 'done', others to 'in-progress'")
    report.append("")
    report.append("SHORT-TERM ACTIONS (Priority 2):")
    report.append("3. Address abandoned features")
    report.append(
        "   - "
        + str(len(analysis["abandoned_features"]))
        + " features in 'todo' with no work"
    )
    report.append("   - Archive or start work within 1 week")
    report.append("")
    report.append("4. Implement post-step-completion hook")
    report.append("   - Auto-update feature status when all steps complete")
    report.append("   - Prevent future status drift")
    report.append("")
    report.append("LONG-TERM ACTIONS (Priority 3):")
    report.append("5. Enforce agent attribution at feature creation")
    report.append("   - Update SDK.features.create() to capture agent context")
    report.append("   - Make agent_assigned a required field")
    report.append("")
    report.append("6. Add validation tests")
    report.append("   - Test for status/step mismatches")
    report.append("   - Test for untracked features")
    report.append("   - Prevent regression")
    report.append("")

    return "\n".join(report)


if __name__ == "__main__":
    features, analysis = analyze_features()
    report = generate_report(features, analysis)
    print(report)

    # Save report
    report_path = Path(
        "/Users/shakes/DevProjects/htmlgraph/FEATURE_INTEGRITY_ANALYSIS.md"
    )
    report_path.write_text(report)
    print(f"\n\nReport saved to: {report_path}")

    # Summary for display
    print("\n\nQUICK STATS:")
    print(
        f"Total issues found: {len(features) - sum(1 for f in features if f.status == 'done' and f.steps_completed == f.steps_total)}"
    )
    print(f"- Abandoned: {len(analysis['abandoned_features'])}")
    print(f"- Partially done: {len(analysis['partially_done'])}")
    print(f"- Status mismatch: {len(analysis['status_mismatch'])}")
    print(f"- Untracked work: {len(analysis['untracked_work'])}")
    print(f"- Untracked features: {len(analysis['untracked_features'])}")
