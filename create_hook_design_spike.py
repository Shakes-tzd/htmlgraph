#!/usr/bin/env python3
"""Create spike documenting hook integration design for auto-injection"""

from htmlgraph import SDK
import json

sdk = SDK(agent='designer-hooks')

findings = '''
# Hook Integration Design for Auto-Injection of Documentation

## 1. Hook Selection Strategy

### Primary Hooks (Implement First)

**SessionStart** - Minimal Context Bootstrap
- **Purpose**: Establish baseline understanding without overwhelming context
- **Token Budget**: 150-250 tokens
- **Trigger**: Every new session
- **Injection**: Quick reference card + active work context

**PreToolUse** - Just-In-Time Documentation
- **Purpose**: Inject relevant docs right before tool execution
- **Token Budget**: 100-200 tokens per injection
- **Trigger**: Tool name pattern matching
- **Injection**: Method-specific docs + common pitfalls

**UserPromptSubmit** - Keyword-Triggered Help
- **Purpose**: Respond to implicit documentation requests
- **Token Budget**: 200-400 tokens per injection
- **Trigger**: Keyword/intent detection
- **Injection**: Workflow-specific guides

### Secondary Hooks (Future Enhancement)

**PostToolUse** - Error-Driven Documentation
- **Purpose**: Inject troubleshooting docs after failures
- **Token Budget**: 150-300 tokens
- **Trigger**: Tool execution errors
- **Injection**: Error-specific resolution guides

**SessionEnd** - Cleanup & Best Practices
- **Purpose**: Reinforce patterns before session closes
- **Token Budget**: 100-150 tokens
- **Trigger**: Session termination
- **Injection**: Session summary tips

---

## 2. Injection Rules with Token Budgets

### SessionStart Injection (150-250 tokens)

```xml
<htmlgraph_context>
<quick_reference>
# HtmlGraph Quick Reference (v{version})

## SDK Operations (Most Common)
- Feature: sdk.features.create("title").set_priority("high").save()
- Spike: sdk.spikes.create("title").set_spike_type("RESEARCH").save()
- Track: sdk.tracks.create("name").add_features([ids]).save()
- Analytics: sdk.analytics.recommend_next_work()

## Current Session
Session: {session_id}
Active Features: {count}
Active Spikes: {count}

## Documentation
Full docs: Call /htmlgraph-docs skill for comprehensive reference
</quick_reference>
</htmlgraph_context>
```

**Injection Logic:**
```python
def on_session_start(session_id: str) -> str:
    active_features = sdk.features.list(status='in-progress')
    active_spikes = sdk.spikes.list(status='active')

    return f"""
<htmlgraph_context>
Session {session_id} started.

Quick Reference:
- sdk.features.create("title") - Create feature
- sdk.analytics.recommend_next_work() - Get next task

Active: {len(active_features)} features, {len(active_spikes)} spikes
Full docs: /htmlgraph-docs skill
</htmlgraph_context>
""".strip()
```

### PreToolUse Injection (100-200 tokens)

**Pattern Matching:**
```python
TOOL_DOC_MAP = {
    'sdk.features.create': '''
<method_docs>
sdk.features.create(title: str) -> FeatureBuilder
  .set_priority("high"|"medium"|"low")
  .set_status("todo"|"in-progress"|"done")
  .add_steps(["step1", "step2"])
  .save() -> Feature

Common pattern:
  feature = sdk.features.create("Auth system")
    .set_priority("high")
    .add_steps(["Design API", "Implement"])
    .save()
</method_docs>
''',

    'sdk.spikes.create': '''
<method_docs>
sdk.spikes.create(title: str) -> SpikeBuilder
  .set_spike_type("RESEARCH"|"ARCHITECTURAL"|"EXPERIMENT")
  .set_findings(markdown_string)
  .save() -> Spike

Common pattern:
  spike = sdk.spikes.create("OAuth investigation")
    .set_spike_type("RESEARCH")
    .set_findings("""# Findings
    - Library X supports OAuth 2.0
    """)
    .save()
</method_docs>
''',

    'sdk.analytics.recommend_next_work': '''
<method_docs>
sdk.analytics.recommend_next_work(
  strategy: str = "balanced",  # "balanced"|"bottleneck"|"quick_wins"
  limit: int = 5
) -> List[WorkItem]

Returns prioritized work items based on:
- Dependency graphs (unblock others)
- Effort estimates (quick wins)
- Strategic value (high priority)

Example:
  recommendations = sdk.analytics.recommend_next_work(strategy="bottleneck")
  for item in recommendations:
      print(f"{item.title}: {item.reason}")
</method_docs>
'''
}

def on_pre_tool_use(tool_name: str) -> Optional[str]:
    # Pattern matching for SDK methods
    for pattern, docs in TOOL_DOC_MAP.items():
        if pattern in tool_name.lower():
            return docs
    return None
```

### UserPromptSubmit Injection (200-400 tokens)

**Keyword Detection:**
```python
KEYWORD_WORKFLOW_MAP = {
    ('create', 'feature'): '''
<workflow_guide>
# Feature Creation Workflow

1. Create feature:
   feature = sdk.features.create("Feature title")

2. Set metadata:
   .set_priority("high"|"medium"|"low")
   .set_status("todo"|"in-progress"|"done")
   .add_dependencies([feature_ids])  # Optional

3. Add implementation steps:
   .add_steps([
       "Design API endpoints",
       "Implement business logic",
       "Add tests"
   ])

4. Save:
   .save()

5. Track in session (automatic via hooks)

Example:
  feature = sdk.features.create("User authentication")
    .set_priority("high")
    .add_steps(["OAuth flow", "JWT tokens", "Tests"])
    .save()
</workflow_guide>
''',

    ('mark', 'complete', 'step'): '''
<workflow_guide>
# Step Completion Workflow

Method 1 - Update feature object:
  feature = sdk.features.get(feature_id)
  feature.complete_step(step_index=0)
  feature.save()

Method 2 - Direct update:
  sdk.features.update(feature_id, {
      'steps': [
          {'description': 'Design API', 'completed': True},
          {'description': 'Implement', 'completed': False}
      ]
  })

Method 3 - Fluent API:
  sdk.features.get(feature_id)
    .complete_step(0)
    .complete_step(1)
    .save()
</workflow_guide>
''',

    ('track', 'planning'): '''
<workflow_guide>
# Track Planning with TrackBuilder

1. Create track:
   track = sdk.tracks.create("Track name")

2. Add features:
   .add_features([feature_id_1, feature_id_2])
   .add_features([feature_id_3])  # Chainable

3. Set metadata:
   .set_description("Track goal")
   .set_status("planning"|"active"|"done")

4. Save:
   .save()

5. Analyze dependencies:
   deps = track.get_dependency_graph()
   bottlenecks = track.find_bottlenecks()

Example:
  track = sdk.tracks.create("Q1 Auth System")
    .add_features([auth_feat_id, session_feat_id])
    .set_description("Complete authentication system")
    .save()
</workflow_guide>
'''
}

def on_user_prompt_submit(prompt: str) -> Optional[str]:
    prompt_lower = prompt.lower()

    for keywords, workflow in KEYWORD_WORKFLOW_MAP.items():
        if all(kw in prompt_lower for kw in keywords):
            return workflow

    return None
```

---

## 3. Context Budget Management

### Budget Allocation (Total: 10k-20k tokens)

```python
class ContextBudgetManager:
    TOTAL_BUDGET = 15_000  # tokens

    ALLOCATIONS = {
        'session_start': 250,      # One-time per session
        'pre_tool_use': 200,       # Per tool invocation
        'user_prompt': 400,        # Per keyword match
        'post_tool_error': 300,    # Per error
        'reserved': 2_000          # Safety buffer
    }

    def __init__(self):
        self.used = 0
        self.injections = []

    def can_inject(self, injection_type: str) -> bool:
        budget = self.ALLOCATIONS.get(injection_type, 0)
        return (self.used + budget) < (self.TOTAL_BUDGET - self.ALLOCATIONS['reserved'])

    def record_injection(self, injection_type: str, tokens: int):
        self.used += tokens
        self.injections.append({
            'type': injection_type,
            'tokens': tokens,
            'timestamp': datetime.now()
        })

    def get_utilization(self) -> float:
        return self.used / self.TOTAL_BUDGET
```

### Priority System (When Over Budget)

```python
INJECTION_PRIORITIES = {
    'session_start': 10,        # Highest - always inject
    'pre_tool_use': 8,          # High - just-in-time help
    'user_prompt': 6,           # Medium - user requested
    'post_tool_error': 7,       # High - error recovery
    'session_end': 3            # Low - nice to have
}

def should_inject(budget_mgr, injection_type: str) -> bool:
    if not budget_mgr.can_inject(injection_type):
        priority = INJECTION_PRIORITIES[injection_type]
        if priority >= 8:  # Critical injections
            # Evict lower priority injections
            budget_mgr.evict_lowest_priority()
            return True
        return False
    return True
```

---

## 4. Dynamic Injection Mechanism

### Hook Implementation (Claude Code Plugin)

```python
# packages/claude-plugin/.claude/hooks/documentation-injection.py

from htmlgraph import SDK
from htmlgraph.hooks import BaseHook
from typing import Optional
import re

class DocumentationInjectionHook(BaseHook):
    def __init__(self):
        self.sdk = SDK(agent='hook-docs')
        self.budget_manager = ContextBudgetManager()
        self.cache = LRUCache(maxsize=50)

    def on_session_start(self, context: dict) -> Optional[str]:
        """Inject minimal context at session start"""
        if not self.budget_manager.can_inject('session_start'):
            return None

        # Check cache
        cache_key = f"session_start_{self.sdk.version}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Generate context
        session_id = context['session_id']
        active_features = len(self.sdk.features.list(status='in-progress'))
        active_spikes = len(self.sdk.spikes.list(status='active'))

        injection = f"""
<htmlgraph_context>
Session {session_id} started.

Quick Reference:
- sdk.features.create("title") - Create feature
- sdk.spikes.create("title") - Create spike
- sdk.analytics.recommend_next_work() - Get recommendations

Active: {active_features} features, {active_spikes} spikes
Full docs: /htmlgraph-docs skill
</htmlgraph_context>
""".strip()

        # Cache and record
        self.cache[cache_key] = injection
        self.budget_manager.record_injection('session_start', 200)

        return injection

    def on_pre_tool_use(self, context: dict) -> Optional[str]:
        """Inject tool-specific docs before execution"""
        tool_name = context.get('tool_name', '')

        if not tool_name.startswith('sdk.'):
            return None

        if not self.budget_manager.can_inject('pre_tool_use'):
            return None

        # Check cache
        cache_key = f"tool_docs_{tool_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Find matching docs
        for pattern, docs in TOOL_DOC_MAP.items():
            if pattern in tool_name:
                self.cache[cache_key] = docs
                self.budget_manager.record_injection('pre_tool_use', 150)
                return docs

        return None

    def on_user_prompt_submit(self, context: dict) -> Optional[str]:
        """Inject workflow docs based on keywords"""
        prompt = context.get('prompt', '').lower()

        if not self.budget_manager.can_inject('user_prompt'):
            return None

        # Keyword matching
        for keywords, workflow in KEYWORD_WORKFLOW_MAP.items():
            if all(kw in prompt for kw in keywords):
                # Don't cache user prompts (too variable)
                self.budget_manager.record_injection('user_prompt', 300)
                return workflow

        return None
```

### Hook Registration (plugin.json)

```json
{
  "name": "htmlgraph",
  "version": "0.9.4",
  "hooks": [
    {
      "type": "SessionStart",
      "script": "hooks/documentation-injection.py",
      "method": "on_session_start"
    },
    {
      "type": "PreToolUse",
      "script": "hooks/documentation-injection.py",
      "method": "on_pre_tool_use"
    },
    {
      "type": "UserPromptSubmit",
      "script": "hooks/documentation-injection.py",
      "method": "on_user_prompt_submit"
    }
  ]
}
```

---

## 5. Caching Strategy

### LRU Cache with TTL

```python
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib

class TTLCache:
    def __init__(self, maxsize: int = 100, ttl_seconds: int = 3600):
        self.cache = {}
        self.maxsize = maxsize
        self.ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]  # Expired
        return None

    def set(self, key: str, value: str):
        if len(self.cache) >= self.maxsize:
            # Evict oldest
            oldest_key = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[key] = (value, datetime.now())
```

### Pre-compilation of Common Workflows

```python
# At plugin initialization
PRECOMPILED_WORKFLOWS = {
    'feature_creation': compile_workflow('create_feature.md'),
    'spike_creation': compile_workflow('create_spike.md'),
    'track_planning': compile_workflow('track_planning.md'),
    'step_completion': compile_workflow('complete_steps.md')
}

def compile_workflow(filename: str) -> str:
    """Load and minify workflow docs"""
    path = PLUGIN_ROOT / 'docs' / 'workflows' / filename
    content = path.read_text()

    # Minify: remove extra whitespace, comments
    minified = re.sub(r'\\n\\s+', '\\n', content)
    minified = re.sub(r'<!--.+?-->', '', minified, flags=re.DOTALL)

    return minified.strip()
```

### Cache Warming Strategy

```python
def warm_cache_on_session_start():
    """Pre-load frequently used docs into cache"""
    cache = TTLCache()

    # Most common SDK operations
    for method in ['features.create', 'spikes.create', 'analytics.recommend']:
        docs = get_method_docs(method)
        cache.set(f"sdk.{method}", docs)

    # Most common workflows
    for workflow_name in PRECOMPILED_WORKFLOWS:
        cache.set(f"workflow_{workflow_name}", PRECOMPILED_WORKFLOWS[workflow_name])
```

---

## 6. User Customization

### Override Mechanism

```python
# User's custom hook in .claude/hooks/custom-docs.py

from htmlgraph.hooks import DocumentationInjectionHook

class CustomDocsHook(DocumentationInjectionHook):
    def __init__(self):
        super().__init__()
        self.load_user_overrides()

    def load_user_overrides(self):
        """Load user's custom documentation"""
        custom_docs_path = Path.home() / '.htmlgraph' / 'custom_docs.yaml'

        if custom_docs_path.exists():
            import yaml
            with open(custom_docs_path) as f:
                self.user_docs = yaml.safe_load(f)
        else:
            self.user_docs = {}

    def on_pre_tool_use(self, context: dict) -> Optional[str]:
        """Check user overrides first, then fallback to package docs"""
        tool_name = context.get('tool_name', '')

        # User override?
        if tool_name in self.user_docs.get('tool_overrides', {}):
            return self.user_docs['tool_overrides'][tool_name]

        # Fallback to package docs
        return super().on_pre_tool_use(context)
```

### User Configuration File (~/.htmlgraph/custom_docs.yaml)

```yaml
# User-specific documentation overrides
tool_overrides:
  sdk.features.create: |
    <custom_docs>
    # My Custom Feature Creation Pattern

    I always use this pattern:
      feature = sdk.features.create("title")
        .set_priority("high")  # I default to high priority
        .add_labels(["project-x"])  # My project label
        .save()
    </custom_docs>

workflow_overrides:
  feature_creation: |
    <custom_workflow>
    # My Feature Workflow

    1. Create feature with project label
    2. Add to current sprint track
    3. Link to Jira ticket
    </custom_workflow>

injection_preferences:
  session_start: true       # Always inject at session start
  pre_tool_use: true        # Always inject before SDK calls
  user_prompt: false        # Disable keyword-triggered injection (I'll call /htmlgraph-docs explicitly)
  max_injections_per_session: 10  # Hard limit
```

### Merging Package Updates with User Overrides

```python
def merge_docs(package_docs: dict, user_docs: dict) -> dict:
    """Merge user overrides with package docs"""
    merged = package_docs.copy()

    # User overrides take precedence
    if 'tool_overrides' in user_docs:
        merged.setdefault('tool_overrides', {}).update(user_docs['tool_overrides'])

    if 'workflow_overrides' in user_docs:
        merged.setdefault('workflow_overrides', {}).update(user_docs['workflow_overrides'])

    # Preferences override package defaults
    if 'injection_preferences' in user_docs:
        merged['preferences'] = user_docs['injection_preferences']

    return merged
```

---

## 7. Performance Targets

### Latency Budgets

```python
LATENCY_BUDGETS = {
    'session_start': 50,      # ms - One-time cost acceptable
    'pre_tool_use': 20,       # ms - Can't delay tool execution
    'user_prompt': 30,        # ms - User expects fast response
    'post_tool_error': 40,    # ms - Error recovery context
}

class PerformanceMonitor:
    def __init__(self):
        self.timings = []

    def measure(self, hook_type: str):
        """Context manager for measuring hook performance"""
        return HookTimer(hook_type, self)

    def record(self, hook_type: str, duration_ms: float):
        self.timings.append({
            'hook_type': hook_type,
            'duration_ms': duration_ms,
            'timestamp': datetime.now()
        })

        # Alert if over budget
        if duration_ms > LATENCY_BUDGETS.get(hook_type, 50):
            logger.warning(f"{hook_type} hook exceeded budget: {duration_ms}ms")

class HookTimer:
    def __init__(self, hook_type: str, monitor: PerformanceMonitor):
        self.hook_type = hook_type
        self.monitor = monitor
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        duration_ms = (time.perf_counter() - self.start) * 1000
        self.monitor.record(self.hook_type, duration_ms)
```

### Optimization Strategies

**1. Lazy Loading**
```python
def on_pre_tool_use(self, context: dict) -> Optional[str]:
    # Don't load docs until pattern matches
    tool_name = context.get('tool_name', '')

    if not tool_name.startswith('sdk.'):
        return None  # Fast exit

    # Only load docs if pattern matches
    return self._get_tool_docs(tool_name)  # Lazy load
```

**2. Async Injection (Future Enhancement)**
```python
async def on_pre_tool_use_async(self, context: dict) -> Optional[str]:
    """Non-blocking documentation injection"""
    tool_name = context.get('tool_name', '')

    # Kick off async doc loading
    docs_future = asyncio.create_task(self._load_docs_async(tool_name))

    # Don't block tool execution
    # Docs will be available in context by the time tool completes
    return await docs_future
```

**3. Pre-computation at Build Time**
```python
# scripts/precompile-docs.py
# Run during package build

def precompile_all_docs():
    """Generate optimized doc bundles at build time"""

    for method in SDK_METHODS:
        docs = extract_method_docs(method)
        minified = minify_docs(docs)

        output_path = PACKAGE_ROOT / 'precompiled' / f'{method}.txt'
        output_path.write_text(minified)

    print(f"Pre-compiled {len(SDK_METHODS)} doc bundles")
```

---

## 8. Example Scenarios with Token Counts

### Scenario 1: Agent Starts Fresh Session

**SessionStart Hook:**
```
Token count: 187 tokens

<htmlgraph_context>
Session abc-123 started.

Quick Reference:
- sdk.features.create("title") - Create feature
- sdk.spikes.create("title") - Create spike
- sdk.analytics.recommend_next_work() - Get recommendations

Active: 3 features, 1 spike
Full docs: /htmlgraph-docs skill
</htmlgraph_context>
```

**Budget Impact:** 187 / 15,000 = 1.2% utilization

---

### Scenario 2: Agent Calls sdk.features.create()

**PreToolUse Hook:**
```
Token count: 143 tokens

<method_docs>
sdk.features.create(title: str) -> FeatureBuilder
  .set_priority("high"|"medium"|"low")
  .add_steps(["step1", "step2"])
  .save() -> Feature

Example:
  feature = sdk.features.create("Auth system")
    .set_priority("high")
    .add_steps(["Design", "Implement"])
    .save()
</method_docs>
```

**Budget Impact:** 330 / 15,000 = 2.2% utilization (cumulative)

---

### Scenario 3: User Asks "How do I create a feature?"

**UserPromptSubmit Hook:**
```
Token count: 287 tokens

<workflow_guide>
# Feature Creation Workflow

1. Create: sdk.features.create("title")
2. Set metadata: .set_priority("high")
3. Add steps: .add_steps(["Step 1", "Step 2"])
4. Save: .save()

Example:
  feature = sdk.features.create("User auth")
    .set_priority("high")
    .add_steps(["OAuth", "JWT", "Tests"])
    .save()
</workflow_guide>
```

**Budget Impact:** 617 / 15,000 = 4.1% utilization (cumulative)

---

### Scenario 4: Agent Works for 30 Minutes (Multiple Operations)

**Cumulative Injections:**
- 1x SessionStart: 187 tokens
- 8x PreToolUse (various SDK calls): 8 × 150 = 1,200 tokens
- 3x UserPrompt (user asked 3 questions): 3 × 280 = 840 tokens
- **Total: 2,227 tokens (14.8% utilization)**

**Still within budget with room for:**
- 85 more PreToolUse injections
- 42 more UserPrompt injections
- Error recovery docs if needed

---

## 9. Platform-Specific Considerations

### Claude Code (Full Hook Support)
- All hooks available (SessionStart, PreToolUse, UserPromptSubmit)
- Context injection via hook return values
- Performance monitoring built-in
- **Recommendation:** Full implementation as designed

### Gemini (Limited Hook Support)
- Hooks may not be available
- **Fallback:** Skill-based documentation (`/htmlgraph-docs` skill)
- **Alternative:** Context files loaded at session start
- **Recommendation:** Pre-load essential docs in GEMINI.md

### API (No Hooks)
- No hook infrastructure
- **Fallback:** Documentation in API responses
- **Alternative:** Client-side doc injection (if using SDK)
- **Recommendation:** Return docs in error responses

---

## 10. Implementation Phases

### Phase 1: Core Hooks (Week 1)
- [ ] Implement SessionStart hook with minimal context
- [ ] Implement PreToolUse hook with method docs
- [ ] Basic cache (LRU, no TTL)
- [ ] Performance monitoring
- [ ] Unit tests for hooks

### Phase 2: User Prompts (Week 2)
- [ ] Implement UserPromptSubmit hook
- [ ] Keyword detection and workflow mapping
- [ ] Context budget management
- [ ] Integration tests

### Phase 3: Optimization (Week 3)
- [ ] TTL cache implementation
- [ ] Pre-compilation of common workflows
- [ ] Cache warming strategy
- [ ] Performance profiling

### Phase 4: Customization (Week 4)
- [ ] User override mechanism
- [ ] Custom docs YAML schema
- [ ] Merge strategy for package updates
- [ ] User documentation

### Phase 5: Advanced Features (Future)
- [ ] PostToolUse error-driven injection
- [ ] Async injection support
- [ ] Platform-specific adapters (Gemini, API)
- [ ] Analytics on injection effectiveness

---

## 11. Success Metrics

### Performance
- [ ] SessionStart injection: <50ms (Target: 30ms)
- [ ] PreToolUse injection: <20ms (Target: 10ms)
- [ ] UserPrompt injection: <30ms (Target: 20ms)
- [ ] Cache hit rate: >80%

### Effectiveness
- [ ] Context utilization: 5-15% of total budget
- [ ] User satisfaction: Fewer "/help" commands
- [ ] Reduced errors: Fewer tool usage mistakes
- [ ] Documentation access: >70% via hooks vs manual lookup

### Adoption
- [ ] 90%+ of users keep hook injection enabled
- [ ] <5% disable due to performance concerns
- [ ] User customization: 20%+ create custom docs

---

## 12. Open Questions & Future Work

**Q1: Should we inject docs for non-SDK tools?**
- Example: Injecting Git workflow docs before git operations?
- **Decision:** Start with SDK-only, expand based on user feedback

**Q2: How to handle multi-language support?**
- Docs currently English-only
- **Future:** i18n support with language detection

**Q3: Should injection be opt-in or opt-out?**
- **Recommendation:** Opt-out (enabled by default, disable in config)
- Provides immediate value to new users

**Q4: Integration with external documentation systems?**
- Example: Fetch docs from company wiki or Confluence
- **Future:** Plugin API for custom doc sources

**Q5: Telemetry and analytics?**
- Track which docs are most injected/useful
- **Privacy concern:** Opt-in only, anonymized

---

## Summary

This design provides:
1. Progressive disclosure - Start minimal, inject more as needed
2. Context efficiency - <15% budget utilization for typical session
3. Performance - <50ms latency per injection
4. Customization - User overrides without breaking package updates
5. Platform compatibility - Works with Claude Code, degrades gracefully for others
6. Offline-first - All docs cached locally
7. Maintainability - Centralized doc source (AGENTS.md) with auto-sync

The system balances token efficiency with useful context, providing just-in-time documentation without overwhelming the agent's context window.
'''

# Create spike
spike = sdk.spikes.create('Design: Hook Integration for Auto-Injection of Documentation') \
    .set_spike_type('ARCHITECTURAL') \
    .set_findings(findings) \
    .save()

print(json.dumps({
    'spike_id': spike.id,
    'title': spike.title,
    'spike_type': spike.spike_type,
    'status': spike.status,
    'findings_length': len(spike.findings),
    'message': 'Hook integration design spike created successfully'
}, indent=2))
