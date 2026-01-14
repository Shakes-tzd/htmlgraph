from __future__ import annotations

"""
Utility functions for work type inference and classification.

Provides automatic work type detection based on active work items.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph import SDK


def infer_work_type_from_id(feature_id: str | None) -> str | None:
    """
    Automatically infer work type from feature/bug/spike/chore ID prefix.

    Args:
        feature_id: ID of active work item (e.g., "feat-123", "spike-456")

    Returns:
        WorkType enum value, or None if cannot infer

    Examples:
        >>> infer_work_type_from_id("feat-abc123")
        "feature-implementation"

        >>> infer_work_type_from_id("spike-xyz789")
        "spike-investigation"

        >>> infer_work_type_from_id("bug-456")
        "bug-fix"

        >>> infer_work_type_from_id("chore-789")
        "maintenance"

        >>> infer_work_type_from_id(None)
        None
    """
    from htmlgraph.models import WorkType

    if not feature_id:
        return None

    # Infer from ID prefix
    if feature_id.startswith("feat-") or feature_id.startswith("feature-"):
        return WorkType.FEATURE.value
    elif feature_id.startswith("spike-"):
        return WorkType.SPIKE.value
    elif feature_id.startswith("bug-"):
        return WorkType.BUG_FIX.value
    elif feature_id.startswith("chore-"):
        return WorkType.MAINTENANCE.value
    elif feature_id.startswith("doc-") or "documentation" in feature_id.lower():
        return WorkType.DOCUMENTATION.value
    elif feature_id.startswith("plan-") or "planning" in feature_id.lower():
        return WorkType.PLANNING.value

    return None


def infer_work_type(feature_id: str | None, sdk: SDK | None = None) -> str | None:
    """
    Infer work type from active work item, with optional SDK lookup for details.

    First tries ID-based inference. If SDK is provided, can look up the actual
    work item to get more specific classification (e.g., spike_type, maintenance_type).

    Args:
        feature_id: ID of active work item
        sdk: Optional SDK instance for detailed lookup

    Returns:
        WorkType enum value, or None if cannot infer

    Examples:
        >>> infer_work_type("feat-123")
        "feature-implementation"

        >>> # With SDK, can get more specific types
        >>> sdk = SDK()
        >>> infer_work_type("spike-456", sdk)
        "spike-investigation"  # Could differentiate technical/architectural/risk
    """
    from htmlgraph.models import WorkType

    # First try simple ID-based inference
    work_type = infer_work_type_from_id(feature_id)
    if work_type or not sdk:
        return work_type

    # If SDK provided, try detailed lookup
    # (Future enhancement: check spike_type, maintenance_type for more specific classification)
    if not feature_id:
        return None

    try:
        if feature_id.startswith("spike-"):
            # Could check spike.spike_type to differentiate TECHNICAL/ARCHITECTURAL/RISK
            # For now, just return SPIKE
            return WorkType.SPIKE.value
        elif feature_id.startswith("chore-"):
            # Could check chore.maintenance_type to differentiate maintenance types
            # For now, just return MAINTENANCE
            return WorkType.MAINTENANCE.value
    except Exception:
        # If lookup fails, fall back to None
        pass

    return None
