---
name: Plan YAML is writable authored content
description: .htmlgraph/plans/*.yaml are agent-editable working documents, not SDK-managed state
type: feedback
---

Plan YAML files are the agent's working document — read, modify via yaml.safe_load/dump, commit to git. The write guard has a carve-out for them.

**Why:** YAML plans are authored content like code. HTML work items are canonical records written only by the Go CLI. The guard should block HTML/DB writes but allow plan YAML edits.

**How to apply:** When editing plans, use Python yaml.safe_load → modify dict → yaml.dump. No need for CLI update commands — git diff provides the audit trail. Commit after each revision.
