#!/usr/bin/env python3
"""
Create HtmlGraph spike for Feature Tracking Data Integrity Analysis
"""

import uuid
from datetime import datetime
from pathlib import Path

# Read the analysis report
analysis_report = Path("/Users/shakes/DevProjects/htmlgraph/FEATURE_INTEGRITY_ANALYSIS.md").read_text()

# Create spike HTML
spike_id = f"spk-{uuid.uuid4().hex[:8]}"
timestamp = datetime.now().isoformat()

spike_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="htmlgraph-version" content="1.0">
    <title>Feature Tracking Data Integrity Analysis</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <article id="{spike_id}"
             data-type="spike"
             data-status="completed"
             data-priority="high"
             data-created="{timestamp}"
             data-updated="{timestamp}"
             data-agent-assigned="claude"
             data-claimed-by-session="sess-analysis">

        <header>
            <h1>Feature Tracking Data Integrity Analysis</h1>
            <div class="metadata">
                <span class="badge status-completed">Completed</span>
                <span class="badge priority-high">High Priority</span>
            </div>
        </header>

        <section data-findings>
            <h2>Executive Summary</h2>
            <p><strong>Status:</strong> 65 of 89 features (73.0%) have data integrity issues</p>
            <ul>
                <li><strong>33 abandoned features</strong> - Created but never worked on (todo, 0 steps)</li>
                <li><strong>14 status mismatches</strong> - Marked 'done' but have incomplete steps</li>
                <li><strong>18 untracked work items</strong> - All steps completed but no agent attribution</li>
                <li><strong>64 untracked features</strong> - No agent_assigned metadata (71.9%)</li>
            </ul>

            <h2>Status Distribution</h2>
            <ul>
                <li>Done: 54 features (60.7%)</li>
                <li>Todo: 34 features (38.2%)</li>
                <li>In-progress: 1 feature (1.1%)</li>
            </ul>

            <h2>Agent Attribution Analysis</h2>
            <ul>
                <li>Features with agent assigned: 25 (28.1%)</li>
                <li>Features WITHOUT agent assigned: 64 (71.9%)</li>
            </ul>

            <p><strong>Agents who created features:</strong></p>
            <ul>
                <li>claude: 6 features</li>
                <li>claude-code: 5 features</li>
                <li>cli: 5 features</li>
                <li>orchestrator: 4 features</li>
                <li>claude-orchestrator: 3 features</li>
                <li>test: 1 feature</li>
                <li>test-agent: 1 feature</li>
            </ul>

            <h2>Root Causes</h2>

            <h3>1. Abandoned Work (33 features, 37.1%)</h3>
            <p><strong>Problem:</strong> Features created but never started (status=todo, 0 steps completed)</p>
            <p><strong>Likely causes:</strong></p>
            <ul>
                <li>Features created but then deprioritized</li>
                <li>Features not assigned to anyone for execution</li>
                <li>Work started in external system (Slack, email) instead of tracking here</li>
                <li>Bulk feature creation during planning sessions without follow-up</li>
            </ul>

            <h3>2. Status Drift (14 features, 15.7%)</h3>
            <p><strong>Problem:</strong> Features marked 'done' but have incomplete steps</p>
            <p><strong>Likely causes:</strong></p>
            <ul>
                <li>Features marked done without verifying all steps are complete</li>
                <li>Steps added AFTER feature was marked done</li>
                <li>Steps not properly marked as completed (data-completed="true")</li>
                <li>No workflow to enforce step completion before marking feature done</li>
            </ul>

            <h3>3. Missing Agent Attribution (64 features, 71.9%)</h3>
            <p><strong>Problem:</strong> No agent_assigned metadata on features</p>
            <p><strong>Likely causes:</strong></p>
            <ul>
                <li>Features created directly via HTML instead of SDK.features.create()</li>
                <li>Agent metadata not captured during feature creation</li>
                <li>Features created before agent attribution was implemented</li>
                <li>Manual file migrations lost metadata</li>
            </ul>

            <h3>4. Untracked Work (18 features, 20.2%)</h3>
            <p><strong>Problem:</strong> Work fully completed but no agent attribution</p>
            <p><strong>Likely causes:</strong></p>
            <ul>
                <li>Steps completed but feature not created with agent context</li>
                <li>Work completed before feature was tracked</li>
                <li>SDK not called with agent parameter during creation</li>
            </ul>

            <h2>Detailed Issue List</h2>

            <h3>Abandoned Features Examples (33 total)</h3>
            <ul>
                <li>feat-2e724483: Add CLI integration tests for output modes</li>
                <li>feat-48b88f74: Add PreCompact Workarounds for Work Preservation</li>
                <li>feat-4d2a6e2f: Add Systematic Change Checklist to PR Template</li>
                <li>feat-385e17e2: Add htmlgraph claude --init/--continue CLI commands</li>
                <li>feat-c3d11521: Auto-sync dashboard.html to index.html in serve command</li>
                <li>feat-64467b2c: Convert list commands to Rich tables</li>
                <li>feat-66d73d8c: Create Systematic Refactoring Scripts</li>
                <li>feat-e75b27e2: Document Current Orchestrator Approach as Best Practice</li>
                <li>feat-af04a486: Document Systematic Change Workflow in RULES.md</li>
                <li>... and 24 more</li>
            </ul>

            <h3>Status Mismatch Examples (14 total) - Done But Incomplete Steps</h3>
            <ul>
                <li>feat-2fb22d44: Deploy HtmlGraph with CLI orchestration injection (0/3 steps)</li>
                <li>feat-0a49152e: Add SDK wrappers for operations layer (0/3 steps)</li>
                <li>feat-c00bc6c0: Commit CLI orchestration rules injection (0/3 steps)</li>
                <li>feat-dca81f7c: Refactor CLI to use SDK/operations backend (0/3 steps)</li>
                <li>feat-0888e0f1: Inject orchestration rules via CLI --append-system-prompt (0/4 steps)</li>
                <li>feat-839eb731: Add Node.to_dict() method as alias to model_dump() (0/6 steps)</li>
                <li>feat-1b4eb0c7: Add /error-analysis slash command (0/7 steps)</li>
                <li>feat-08b7bf72: Add comprehensive docstrings to BaseCollection methods (0/8 steps)</li>
                <li>feat-977c5400: Agent Delegation & Parallel Execution System (0/8 steps)</li>
                <li>... and 5 more</li>
            </ul>

            <h3>Untracked Work Examples (18 total) - Complete But No Agent</h3>
            <ul>
                <li>feat-bda2afc3: Packageable auto-updating agent documentation system (10/10 steps)</li>
                <li>feat-d50a0e5e: Restore project-specific knowledge to CLAUDE.md (10/10 steps)</li>
                <li>feat-23928549: Enhance system prompt with HtmlGraph (8/8 steps)</li>
                <li>feat-3b3acc91: Fix orchestrator delegation (8/8 steps)</li>
                <li>feat-71a3be23: Deploy enhanced system prompt (8/8 steps)</li>
                <li>feat-150b5351: Publish orchestrator system to plugin (7/7 steps)</li>
                <li>feat-e9f7d60b: Fix orchestrator enforcement bypasses (7/7 steps)</li>
                <li>feat-1c910b0d: Phase 1: Enhanced Event Data Schema (6/6 steps)</li>
                <li>feat-8c539996: Fix SessionStart hook (6/6 steps)</li>
                <li>... and 9 more</li>
            </ul>

            <h2>Repair Strategy</h2>

            <h3>Category 1: Auto-Fixable (No Manual Review Needed)</h3>
            <p>None identified - all issues require review or process changes</p>

            <h3>Category 2: Requires Manual Review (Immediate)</h3>
            <ul>
                <li>
                    <strong>Status mismatch features (14 items):</strong>
                    <ul>
                        <li>Review each feature marked 'done' with incomplete steps</li>
                        <li>Either: (a) complete missing steps, or (b) change status to 'todo'/'in-progress'</li>
                        <li>Estimated effort: 1-2 hours</li>
                    </ul>
                </li>
                <li>
                    <strong>Abandoned features (33 items):</strong>
                    <ul>
                        <li>Review each 'todo' feature with 0 steps completed</li>
                        <li>Either: (a) start work and mark 'in-progress', or (b) archive/delete</li>
                        <li>Estimated effort: 2-3 hours</li>
                    </ul>
                </li>
            </ul>

            <h3>Category 3: Process Improvements (Long-Term)</h3>
            <ul>
                <li>
                    <strong>Add agent attribution enforcement:</strong>
                    <ul>
                        <li>Update SDK.features.create() to capture current agent from context</li>
                        <li>Make agent_assigned a required field on features</li>
                        <li>Add validation to reject features without agent</li>
                        <li>Prevents future untracked work</li>
                    </ul>
                </li>
                <li>
                    <strong>Implement status sync hook:</strong>
                    <ul>
                        <li>Create hook that auto-updates feature status when all steps complete</li>
                        <li>When step marked complete, check if all steps done → auto-promote status to 'done'</li>
                        <li>Prevents status drift</li>
                    </ul>
                </li>
                <li>
                    <strong>Add validation tests:</strong>
                    <ul>
                        <li>Test for status/step mismatches</li>
                        <li>Test for untracked features (no agent_assigned)</li>
                        <li>Test for abandoned features (todo, 0 steps)</li>
                        <li>Prevent regression going forward</li>
                    </ul>
                </li>
            </ul>

            <h2>Action Plan</h2>

            <h3>Priority 1 - Fix Existing Data (1 week)</h3>
            <ol>
                <li>Address 14 status mismatch features
                    <ul>
                        <li>Review each one</li>
                        <li>Either complete missing steps OR change status</li>
                        <li>Update data-status and data-completed attributes</li>
                    </ul>
                </li>
                <li>Triage 33 abandoned features
                    <ul>
                        <li>Archive obsolete features</li>
                        <li>Start high-priority ones (mark in-progress)</li>
                        <li>Leave low-priority ones in todo (ok for backlog)</li>
                    </ul>
                </li>
            </ol>

            <h3>Priority 2 - Add Missing Attribution (1-2 weeks)</h3>
            <ol>
                <li>Identify which 18 "untracked work" features can have agent assigned retroactively</li>
                <li>Add data-agent-assigned based on git log or commit history</li>
                <li>If unknown, assign to 'unknown-agent' placeholder</li>
            </ol>

            <h3>Priority 3 - Implement Prevention (2-4 weeks)</h3>
            <ol>
                <li>Implement agent attribution requirement in SDK</li>
                <li>Create status sync hook</li>
                <li>Add validation tests</li>
                <li>Document workflow for future feature creation</li>
            </ol>

            <h2>Key Findings</h2>
            <ul>
                <li><strong>73% of features have issues</strong> - This is a systemic problem, not edge cases</li>
                <li><strong>Missing agent attribution is widespread</strong> (71.9%) - Pre-dates agent implementation</li>
                <li><strong>Status/step mismatches</strong> indicate lack of enforcement between these two fields</li>
                <li><strong>Large abandoned backlog</strong> (37% in todo) suggests planning/prioritization issue</li>
                <li><strong>Untracked work despite completion</strong> shows SDK wasn't used during creation</li>
            </ul>

            <h2>Recommendations</h2>
            <p><strong>Short-term (This week):</strong></p>
            <ul>
                <li>Fix 14 status mismatch features - quick wins</li>
                <li>Archive obviously obsolete features from the 33 abandoned list</li>
                <li>Move high-priority abandoned features to in-progress</li>
            </ul>

            <p><strong>Medium-term (This month):</strong></p>
            <ul>
                <li>Implement agent attribution requirement in SDK</li>
                <li>Retroactively assign agents to 18 untracked work items</li>
                <li>Create status sync hook to prevent future drift</li>
            </ul>

            <p><strong>Long-term (Ongoing):</strong></p>
            <ul>
                <li>Maintain discipline: always use SDK.features.create() with agent context</li>
                <li>Review feature backlog monthly - archive, prioritize, or start work</li>
                <li>Add validation tests to CI/CD pipeline</li>
            </ul>

        </section>

        <section data-analysis-metadata>
            <h2>Analysis Metadata</h2>
            <dl>
                <dt>Analysis Date</dt>
                <dd>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</dd>
                <dt>Total Features Analyzed</dt>
                <dd>89</dd>
                <dt>Issues Found</dt>
                <dd>65 (73.0%)</dd>
                <dt>Tools Used</dt>
                <dd>Python regex analysis of HTML feature files</dd>
            </dl>
        </section>

    </article>
</body>
</html>
"""

# Save spike
spike_path = Path(f"/Users/shakes/DevProjects/htmlgraph/.htmlgraph/spikes/{spike_id}.html")
spike_path.write_text(spike_html)

print(f"Spike created: {spike_id}")
print(f"Location: {spike_path}")
print("\nFull analysis report also saved to:")
print("  /Users/shakes/DevProjects/htmlgraph/FEATURE_INTEGRITY_ANALYSIS.md")
print("\nKey Findings:")
print("  - Total issues: 65 of 89 features (73.0%)")
print("  - Abandoned features: 33 (37.1%)")
print("  - Status mismatches: 14 (15.7%)")
print("  - Untracked work: 18 (20.2%)")
print("  - Untracked features (no agent): 64 (71.9%)")
