# /htmlgraph:feature-primary

Set the primary feature for activity attribution.

## Usage

```
/htmlgraph:feature-primary <feature-id>
```

## Arguments

- `feature-id` (required): The feature ID to set as primary

## Instructions for Claude

When multiple features are in progress, this command sets which one receives activity attribution by default.

### Set primary:
```bash
htmlgraph feature primary <feature-id>
```

### After setting:
```markdown
## Primary Feature Set

**ID:** {feature_id}
**Title:** {title}

All subsequent activity will be attributed to this feature unless it matches another feature's patterns better.

### Other Active Features
{List other in-progress features}
```
