📋 Kanban Policy Document

1. Purpose

This document defines how work enters, flows through, and exits our Kanban system.
The goal is to optimize flow, reduce chaos, and make work predictable while allowing flexibility for urgent issues.

⸻

2. Work Item Types

All work must be classified as one of the following:

Type	Purpose	Notes
Bug	Fix incorrect behavior	Must include repro steps
Epic	Track large initiatives	Container only, never flows
Spike	Reduce uncertainty	Time-boxed, ends in decision
Chore	Maintenance / tech debt	First-class work
Hotfix	Emergency production fix	Expedite lane only
Story / Task	Deliver user value	Normal flow item

❗ Epics do not move across the board.

⸻

3. Board Structure

Columns

Backlog
↓
Ready
↓
In Progress (WIP: 3)
↓
Review / Validation (WIP: 2)
↓
Done

Swimlanes (Optional but Recommended)
	•	🚑 Expedite — Hotfixes only
	•	🧠 Discovery — Spikes
	•	🔧 Maintenance — Chores

⸻

4. Entry Policies

Backlog

A card may enter the backlog only if:
	•	Problem is clearly stated
	•	Correct work type is assigned
	•	Acceptance criteria or exit condition exists

Ready

A card may move to Ready only if:
	•	Scope is small enough to complete without handoffs
	•	Dependencies are known
	•	It is actionable now

⸻

5. Pull Policies (How Work Starts)
	•	Work is pulled, never pushed
	•	New work starts only when WIP allows
	•	No individual may have more than 1 active card unless explicitly approved

Pull Order
	1.	🚑 Hotfixes
	2.	Blocked work resolution
	3.	Bugs
	4.	Stories / Features
	5.	Chores

⸻

6. WIP Limits (Non-Negotiable)

Column	Limit
In Progress	3
Review / Validation	2

If WIP is full, help finish work instead of starting new work.

⸻

7. Work-Type-Specific Policies

🐞 Bugs
	•	Must include reproduction steps
	•	Severity affects order, not WIP rules
	•	Critical bugs may bypass backlog but not WIP

⸻

🧱 Epics
	•	Used for tracking and reporting only
	•	Broken into stories, bugs, or chores
	•	Never placed in In Progress

⸻

🔍 Spikes
	•	Time-boxed (max 1–3 days)
	•	Exit criteria:
	•	Decision made
	•	Findings documented
	•	Follow-up cards created or work killed

⸻

🧹 Chores
	•	Treated as first-class work
	•	At least 20% of active work should be maintenance-related
	•	Cannot be deprioritized indefinitely

⸻

🚑 Hotfixes
	•	Used only for production-impacting issues
	•	May exceed WIP limits
	•	Requires:
	•	Root cause analysis
	•	Follow-up corrective work
	•	Visibility to the whole team

⸻

8. Review / Validation Policies

A card may move to Done only if:
	•	Acceptance criteria met
	•	No known regressions introduced
	•	Documentation updated if needed

⸻

9. Metrics We Track

We optimize for flow, not utilization.
	•	Cycle time
	•	Lead time
	•	WIP stability
	•	Throughput
	•	Blocked time

Metrics are used for learning, not performance evaluation.

⸻

10. Explicit Anti-Patterns (What We Avoid)

❌ Epics flowing across the board
❌ Unlimited “In Progress”
❌ Everything marked urgent
❌ Spikes with no output
❌ Chores deferred indefinitely
❌ Individuals optimizing their own speed instead of team flow

⸻

11. Continuous Improvement
	•	Policies are reviewed monthly
	•	Any team member may propose a change
	•	Experiments are encouraged and time-boxed

⸻

12. One-Line Principle

We limit work, finish fast, and learn continuously.

