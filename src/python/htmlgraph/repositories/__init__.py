"""
Repository Pattern Implementation for HtmlGraph.

Provides abstract interfaces and implementations for data access.
Unifies access patterns across SDK, CLI, Collections, and Analytics.

## Core Concepts

**Repository**: Abstract interface for data access
- Hides storage implementation details
- Provides consistent query/filter API
- Manages caching and lifecycle

**Compliance Tests**: Every implementation must pass these
- Identity invariants (object caching)
- ACID properties
- Error handling contracts
- Performance characteristics

## Components

### FeatureRepository
Abstract interface for Feature data access.

```python
from htmlgraph.repositories import FeatureRepository

# Usage (implemented by SDK/Collections)
repo = sdk.features  # Implements FeatureRepository

# Get single feature
feature = repo.get("feat-001")

# List with filters
todo_features = repo.list({"status": "todo"})

# Build complex queries
repo.where(status="todo").where(priority="high").execute()

# Batch operations
repo.batch_update(["f1", "f2"], {"status": "done"})

# Advanced queries
deps = repo.find_dependencies("feat-auth")
blocking = repo.find_blocking("feat-db-migration")

# Cache management
repo.invalidate_cache("feat-001")
repo.reload()
```

## Implementation Guide

To implement FeatureRepository:

1. **Inherit from FeatureRepository**:
   ```python
   class MyFeatureRepository(FeatureRepository):
       def __init__(self, ...):
           self._cache = {}  # Object identity cache
           # ...

       def get(self, feature_id):
           if feature_id in self._cache:
               return self._cache[feature_id]  # Return cached instance
           # Load from storage
           feature = self._load(feature_id)
           if feature:
               self._cache[feature_id] = feature
           return feature
   ```

2. **Implement all abstract methods** with proper signatures

3. **Pass compliance tests**:
   ```python
   class TestMyFeatureRepository(FeatureRepositoryComplianceTests):
       @pytest.fixture
       def repo(self):
           return MyFeatureRepository()
   ```

4. **Contract enforcement**:
   - Identity invariant: `get(id)` returns same instance
   - Atomicity: writes are all-or-nothing
   - Cache sync: cached objects stay in sync with storage
   - Error handling: all exceptions properly raised

## Design Patterns

### Lazy Loading
Features loaded on-demand, not all at once:
```python
feature = repo.get("feat-001")  # Loads only this feature
```

### Caching
Object instances cached for identity:
```python
f1 = repo.get("feat-001")
f2 = repo.get("feat-001")
assert f1 is f2  # Same instance, not copy
```

### Query Building
Fluent interface for complex queries:
```python
results = repo.where(status="todo") \
    .where(priority="high") \
    .execute()
```

### Batch Operations
Vectorized bulk operations for efficiency:
```python
# More efficient than N individual saves
repo.batch_update(["f1", "f2", "f3"], {"status": "done"})
```

### Cache Invalidation
When external processes modify storage:
```python
repo.invalidate_cache()  # Force reload on next access
repo.reload()  # Immediate reload
```

## Contract Invariants

Every FeatureRepository implementation MUST maintain:

1. **Identity Invariant**
   - `get(id)` returns same object instance for same feature
   - Multiple calls return identical object (is, not ==)
   - Supports weak references for memory efficiency

2. **Atomicity**
   - Write operations are atomic (all or nothing)
   - No partial updates on failure
   - Rollback on exception

3. **Consistency**
   - Cache stays in sync with storage
   - Invalidate when external changes detected
   - Reload reconciles state

4. **Isolation**
   - Concurrent reads allowed
   - Concurrent writes serialized
   - No data corruption on race conditions

5. **Error Handling**
   - All errors preserve full context
   - Proper exception types raised
   - No silent failures

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| get(id) | O(1) cached, O(log n) uncached | Identity caching |
| list() | O(n) | Full scan, early termination possible |
| where() | O(n) | Chain builds filters |
| batch_get(k) | O(k) | Vectorized, k = batch size |
| batch_update(k) | O(k) | Vectorized |
| batch_delete(k) | O(k) | Vectorized |
| find_dependencies() | O(n) | Graph traversal |
| count() | O(n) or O(1) | Depends on implementation |
| exists() | O(1) | Optimized check |

## Testing

Run compliance tests:
```bash
pytest tests/unit/repositories/test_feature_repository_compliance.py -v
```

Test concrete implementation:
```bash
pytest tests/unit/repositories/test_my_feature_repository.py -v
```

## See Also

- `feature_repository.py` - Interface definition
- `test_feature_repository_compliance.py` - Compliance test suite
- `src/python/htmlgraph/collections/base.py` - Current implementation
- `src/python/htmlgraph/sdk/collections/features.py` - SDK usage
"""

# Analytics Repository
from .analytics_repository import (
    AnalysisError,
    AnalyticsRepository,
    AnalyticsRepositoryError,
    DependencyAnalysis,
    InvalidItemError,
    WorkRecommendation,
)
from .analytics_repository_standard import StandardAnalyticsRepository
from .feature_repository import (
    FeatureConcurrencyError,
    FeatureNotFoundError,
    FeatureRepository,
    FeatureRepositoryError,
    FeatureValidationError,
    RepositoryQuery,
)
from .feature_repository_htmlfile import HTMLFileFeatureRepository

# Concrete implementations - Features
from .feature_repository_memory import MemoryFeatureRepository
from .feature_repository_sqlite import SQLiteFeatureRepository

# Filter Service
from .filter_service import (
    Filter,
    FilterLogic,
    FilterOperator,
    FilterService,
    FilterServiceError,
    InvalidFilterError,
)
from .filter_service_standard import StandardFilterService

# Shared Cache
from .shared_cache import (
    CacheCapacityError,
    CacheKeyError,
    SharedCache,
    SharedCacheError,
    get_shared_cache,
)
from .shared_cache_memory import MemorySharedCache
from .track_repository import (
    TrackConcurrencyError,
    TrackNotFoundError,
    TrackRepository,
    TrackRepositoryError,
    TrackValidationError,
)
from .track_repository_htmlfile import HTMLFileTrackRepository

# Concrete implementations - Tracks
from .track_repository_memory import MemoryTrackRepository
from .track_repository_sqlite import SQLiteTrackRepository

__all__ = [
    # Feature Repository
    "FeatureRepository",
    "FeatureRepositoryError",
    "FeatureNotFoundError",
    "FeatureValidationError",
    "FeatureConcurrencyError",
    "RepositoryQuery",
    # Feature implementations
    "MemoryFeatureRepository",
    "HTMLFileFeatureRepository",
    "SQLiteFeatureRepository",
    # Track Repository
    "TrackRepository",
    "TrackRepositoryError",
    "TrackNotFoundError",
    "TrackValidationError",
    "TrackConcurrencyError",
    # Track implementations
    "MemoryTrackRepository",
    "HTMLFileTrackRepository",
    "SQLiteTrackRepository",
    # Analytics Repository
    "AnalyticsRepository",
    "DependencyAnalysis",
    "WorkRecommendation",
    "AnalyticsRepositoryError",
    "AnalysisError",
    "InvalidItemError",
    "StandardAnalyticsRepository",
    # Filter Service
    "FilterService",
    "Filter",
    "FilterOperator",
    "FilterLogic",
    "FilterServiceError",
    "InvalidFilterError",
    "StandardFilterService",
    # Shared Cache
    "SharedCache",
    "SharedCacheError",
    "CacheKeyError",
    "CacheCapacityError",
    "get_shared_cache",
    "MemorySharedCache",
]
