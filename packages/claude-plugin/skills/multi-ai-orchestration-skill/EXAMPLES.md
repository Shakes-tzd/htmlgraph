# Multi-AI Orchestration - Real-World Examples

## Example 1: Feature Implementation Workflow

**Scenario:** Implement user authentication with OAuth

```python
from htmlgraph import SDK
from htmlgraph.orchestration import delegate_with_id, get_results_by_task_id

sdk = SDK(agent="orchestrator")

# 1. Create feature (orchestrator does this directly)
feature = sdk.features.create("Add user authentication") \
    .set_priority("high") \
    .save()

# 2. Research phase - use spawn_gemini (fast, cheap)
research_id, research_prompt = delegate_with_id(
    "Research auth patterns",
    """
    Research existing authentication patterns:
    - What library is currently used?
    - Where is validation implemented?
    - What OAuth providers exist?
    """,
    "general-purpose"
)
spawn_gemini(research_prompt)

# 3. Implementation phase - use spawn_codex (code specialist)
impl_id, impl_prompt = delegate_with_id(
    "Implement OAuth",
    f"""
    Implement OAuth based on research:
    - Add JWT auth to API endpoints
    - Create token validation middleware
    - Support Google and GitHub OAuth
    """,
    "general-purpose"
)
spawn_codex(impl_prompt, sandbox="workspace-write")

# 4. Testing phase - use spawn_codex (tests are code)
test_id, test_prompt = delegate_with_id(
    "Write auth tests",
    """
    Write comprehensive tests:
    - Unit tests for middleware
    - Integration tests for OAuth flow
    - E2E tests for user login
    """,
    "general-purpose"
)
spawn_codex(test_prompt, sandbox="workspace-write")

# 5. Git phase - use spawn_copilot (git specialist)
spawn_copilot("Commit and push with message 'feat: add OAuth authentication'")

# 6. Update feature (orchestrator does this directly)
feature.set_status("completed").save()
```

## Example 2: Parallel Analysis Workflow

**Scenario:** Analyze 5 services for performance issues

```python
from concurrent.futures import ThreadPoolExecutor
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

services = ["auth-service", "user-service", "order-service", "payment-service", "notification-service"]

# Spawn parallel analysis with spawn_gemini (cheap, fast)
def analyze_service(service):
    return spawn_gemini(f"""
    Analyze {service} for performance issues:
    - Check response times
    - Identify N+1 queries
    - Find memory leaks
    - Suggest optimizations
    """)

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(analyze_service, services))

# Save consolidated findings
spike = sdk.spikes.create("Performance Analysis: All Services") \
    .set_findings("\n\n".join([
        f"## {svc}\n{result}"
        for svc, result in zip(services, results)
    ])) \
    .save()
```

## Example 3: Architecture Design Workflow

**Scenario:** Design new notification system

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# 1. Architecture design - use spawn_claude (deep reasoning)
design = spawn_claude(
    """
    Design a scalable notification system:

    Requirements:
    - Support email, SMS, push notifications
    - Handle 10M notifications/day
    - Retry failed deliveries
    - Track delivery status

    Provide:
    - System architecture diagram (text)
    - Component breakdown
    - Data flow
    - Technology recommendations
    """,
    permission_mode="plan"  # Safe, no execution
)

# 2. Document design
spike = sdk.spikes.create("Notification System Architecture") \
    .set_findings(design) \
    .save()

# 3. Implementation - delegate to spawn_codex
spawn_codex(f"""
Based on this design:
{design}

Implement the notification service:
1. Create NotificationService class
2. Add email/SMS/push providers
3. Implement retry logic
4. Add status tracking
""", sandbox="workspace-write")
```

## Example 4: PR Review Workflow

**Scenario:** Review and merge a pull request

```python
# 1. Review with spawn_copilot (GitHub specialist)
review = spawn_copilot("""
Review PR #123:
- Check for security issues
- Verify test coverage
- Look for code style violations
- Identify potential bugs

Leave review comments on the PR.
""", allow_tools=["github", "read(*.py)"])

# 2. If approved, merge
spawn_copilot("""
If PR #123 passed review:
- Approve the PR
- Merge to main branch
- Delete the feature branch
""", allow_tools=["github", "shell(git)"])
```

## Example 5: Bug Investigation Workflow

**Scenario:** Debug session timeout issue

```python
from htmlgraph import SDK

sdk = SDK(agent="orchestrator")

# 1. Create bug tracking
bug = sdk.bugs.create("Session timeout too short") \
    .set_priority("critical") \
    .save()

# 2. Investigation - use spawn_gemini (fast document search)
investigation = spawn_gemini("""
Investigate session timeout issue:
- Find session configuration files
- Search for timeout settings
- Check middleware implementation
- Review relevant logs
""")

# 3. Root cause analysis - use spawn_claude (deep reasoning)
analysis = spawn_claude(f"""
Based on investigation:
{investigation}

Determine root cause of session timeout issue.
Users report 5-min timeout, expected 30-min.
""")

# 4. Fix - use spawn_codex (code change)
spawn_codex(f"""
Based on analysis:
{analysis}

Fix session timeout:
1. Update configuration
2. Add test to prevent regression
3. Verify fix works
""", sandbox="workspace-write")

# 5. Commit - use spawn_copilot
spawn_copilot("Commit fix with message 'fix: correct session timeout to 30 minutes'")

# 6. Update bug
bug.set_status("resolved").save()
```

## Example 6: Multi-Model Code Review

**Scenario:** Comprehensive code review using multiple AI models

```python
# 1. Security review - spawn_claude (deep analysis)
security = spawn_claude("""
Security review of src/auth/:
- Identify vulnerabilities
- Check input validation
- Review authentication flow
- Assess data protection
""", permission_mode="plan")

# 2. Performance review - spawn_gemini (fast, cost-effective)
performance = spawn_gemini("""
Performance review of src/auth/:
- Identify slow operations
- Check for N+1 queries
- Find unnecessary computations
- Suggest optimizations
""")

# 3. Code style review - spawn_codex (code specialist)
style = spawn_codex("""
Style review of src/auth/:
- Check naming conventions
- Verify type hints
- Review documentation
- Assess test coverage
""", sandbox="workspace-read")

# 4. Consolidate reviews
sdk = SDK(agent="orchestrator")
spike = sdk.spikes.create("Comprehensive Auth Review") \
    .set_findings(f"""
## Security Review
{security}

## Performance Review
{performance}

## Style Review
{style}
""") \
    .save()
```

## Cost Optimization Summary

| Workflow Type | Recommended Spawner | Why |
|---------------|---------------------|-----|
| Research/Analysis | spawn_gemini | Fast, cheap |
| Code Changes | spawn_codex | Specialized |
| Git Operations | spawn_copilot | GitHub integration |
| Architecture | spawn_claude | Deep reasoning |
| Parallel Work | spawn_gemini | Cost-effective at scale |
