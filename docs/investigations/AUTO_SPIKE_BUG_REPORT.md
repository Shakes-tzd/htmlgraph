# Auto-Spike Bug Report

**Date**: 2025-12-25
**Severity**: 🔴 **CRITICAL**
**Status**: Implementation incomplete - NodeConverter missing field serialization

---

## Bug Summary

The auto-spike system is **partially implemented** with a **critical bug**: the new fields are not persisted to HTML.

### What Works ✅
- Node model has all required fields
- _create_transition_spike() creates spikes with correct fields in memory
- _create_session_init_spike() creates spikes with correct fields in memory

### What's Broken ❌
- **NodeConverter doesn't serialize auto-spike fields to HTML**
- Fields are lost when spike is saved
- Attribution logic fails (needs spike_subtype to identify auto-spikes)
- Lifecycle tracking broken (needs from/to_feature_id)

---

## Evidence

### Test Case: Manual Transition Spike Creation

```python
# Created spike with fields in memory
spike = sm._create_transition_spike(session, from_feature_id='feat-950330cb')

# Expected fields in memory:
spike.spike_subtype = "transition"  ✅
spike.auto_generated = True         ✅
spike.from_feature_id = "feat-950330cb"  ✅
spike.session_id = "sess-7758b1a1"  ✅

# Actual fields in HTML (spk-fc018f3f.html):
data-spike-subtype: MISSING  ❌
data-auto-generated: MISSING  ❌
data-from-feature-id: MISSING  ❌
data-session-id: MISSING  ❌

# Fields when loaded back:
spike.spike_subtype = None  ❌
spike.auto_generated = False  ❌
spike.from_feature_id = None  ❌
```

### HTML Output (Current)

```html
<article id="spk-fc018f3f"
         data-type="spike"
         data-status="in-progress"
         data-priority="low"
         data-created="2025-12-25T04:25:17.003420"
         data-updated="2025-12-25T04:25:17.003423">
<!-- Missing: data-spike-subtype, data-auto-generated, etc. -->
```

### HTML Output (Expected)

```html
<article id="spk-fc018f3f"
         data-type="spike"
         data-status="in-progress"
         data-priority="low"
         data-spike-subtype="transition"
         data-auto-generated="true"
         data-session-id="sess-7758b1a1"
         data-from-feature-id="feat-950330cb"
         data-created="2025-12-25T04:25:17.003420"
         data-updated="2025-12-25T04:25:17.003423">
```

---

## Root Cause Analysis

### 1. NodeConverter Missing Field Mapping

**File**: `src/python/htmlgraph/converter.py`

The converter needs to handle these new fields:
- `spike_subtype` → `data-spike-subtype`
- `auto_generated` → `data-auto-generated`
- `session_id` → `data-session-id`
- `from_feature_id` → `data-from-feature-id`
- `to_feature_id` → `data-to-feature-id`
- `model_name` → `data-model-name`

**Current state**: grep finds ZERO matches for these fields in converter.py

### 2. Impact on Attribution Logic

**File**: `src/python/htmlgraph/session_manager.py:837`

```python
def _get_active_auto_spike(self, active_features: list[Node]) -> Node | None:
    for feature in active_features:
        if (
            feature.type == "spike"
            and feature.auto_generated  # ❌ This is False (not persisted)
            and feature.spike_subtype in ("session-init", "transition")  # ❌ This is None
            and feature.status == "in-progress"
        ):
            return feature
```

**Result**: Auto-spikes are never identified, attribution fails.

### 3. Why feat-950330cb Didn't Get Transition Spike

**Timeline**:
- feat-950330cb completed: 2025-12-25 03:39:14
- Auto-spike code: Added later (uncommitted)
- Transition spike created: NO (code wasn't complete/working)

**Conclusion**: The feature was completed before the auto-spike system was implemented.

---

## Required Fixes

### Fix 1: Update NodeConverter (CRITICAL)

**File**: `src/python/htmlgraph/converter.py`

Add serialization for auto-spike fields:

```python
# In node_to_html() or equivalent:
if node.spike_subtype:
    article_attrs['data-spike-subtype'] = node.spike_subtype
if node.auto_generated:
    article_attrs['data-auto-generated'] = str(node.auto_generated).lower()
if node.session_id:
    article_attrs['data-session-id'] = node.session_id
if node.from_feature_id:
    article_attrs['data-from-feature-id'] = node.from_feature_id
if node.to_feature_id:
    article_attrs['data-to-feature-id'] = node.to_feature_id
if node.model_name:
    article_attrs['data-model-name'] = node.model_name

# In html_to_node() or equivalent:
spike_subtype = article.get('data-spike-subtype')
auto_generated = article.get('data-auto-generated') == 'true'
session_id = article.get('data-session-id')
from_feature_id = article.get('data-from-feature-id')
to_feature_id = article.get('data-to-feature-id')
model_name = article.get('data-model-name')
```

### Fix 2: Test Auto-Spike Lifecycle

Create integration test:
1. Start session → verify session-init spike created with fields
2. Complete feature → verify transition spike created with fields
3. Start feature → verify auto-spikes completed with to_feature_id
4. Verify attribution uses auto-spikes

### Fix 3: Migration for Existing Spike

Delete the broken spike created during testing:
```bash
rm .htmlgraph/spikes/spk-fc018f3f.html
```

---

## Verification Checklist

After fixing NodeConverter:

- [ ] Create session-init spike → verify HTML has all fields
- [ ] Load spike back → verify fields populated correctly
- [ ] Complete feature → verify transition spike has all fields
- [ ] Start feature → verify auto-spikes completed
- [ ] Test attribution → verify auto-spikes identified correctly
- [ ] Run pytest → all tests pass

---

## Updated Status

**Previous assessment**: ✅ Implementation complete
**Actual status**: 🔴 Implementation incomplete

### What's Done ✅
- Node model fields
- SessionManager methods (_create_*, _complete_*, _get_*)
- Trigger points (start_session, complete_feature, start_feature)
- Attribution logic (_get_active_auto_spike)

### What's Missing ❌
- **NodeConverter field serialization** (CRITICAL)
- Integration tests
- End-to-end validation

### Revised Recommendation

1. **Fix NodeConverter** - Add field serialization/deserialization
2. **Test thoroughly** - Verify full lifecycle
3. **Clean up test spike** - Remove spk-fc018f3f.html
4. **Commit together** - SessionManager + Converter changes
5. **Add tests** - Prevent regression

---

## Conclusion

Your observation was **100% correct**: feat-950330cb completion SHOULD have created a transition spike, but it didn't because:

1. **Timing**: Code wasn't complete when feature was completed
2. **Bug**: Even if it had run, fields wouldn't persist (NodeConverter bug)

The auto-spike system is **close to working** but needs the NodeConverter fix to be functional.
