from __future__ import annotations

"""
Hash-based ID generation for HtmlGraph.

Provides collision-resistant IDs for multi-agent collaboration,
inspired by Beads (github.com/steveyegge/beads).

Features:
- Short, human-readable format: {prefix}-{hash} (e.g., feat-a1b2c3d4)
- Content-addressable with entropy for collision resistance
- Hierarchical sub-task support (e.g., feat-a1b2c3d4.1.2)
- Type-specific prefixes for visual identification

With 4 bytes of random entropy + microsecond timestamp + title,
collision probability is effectively zero even with thousands
of concurrent agents creating tasks simultaneously.
"""


import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Literal

# Type alias for valid node types
NodeType = Literal[
    "feature",
    "bug",
    "chore",
    "spike",
    "epic",
    "session",
    "track",
    "phase",
    "agent",
    "spec",
    "plan",
    "event",
]

# Prefix mapping for human readability
# Kept short (3-4 chars) for compact IDs
PREFIXES: dict[str, str] = {
    "feature": "feat",
    "bug": "bug",
    "chore": "chr",
    "spike": "spk",
    "epic": "epc",
    "session": "sess",
    "track": "trk",
    "phase": "phs",
    "agent": "agt",
    "spec": "spec",
    "plan": "plan",
    "event": "evt",  # Activity/event tracking
}

# Reverse mapping for type lookup from prefix
PREFIX_TO_TYPE: dict[str, str] = {v: k for k, v in PREFIXES.items()}

# Regex patterns for ID validation
HASH_ID_PATTERN = re.compile(r"^([a-z]{3,4})-([a-f0-9]{8})(\.\d+)*$")
LEGACY_ID_PATTERN = re.compile(r"^([a-z]+)-(\d{8}-\d{6})$")


def generate_id(
    node_type: str = "feature",
    title: str = "",
    entropy_bytes: int = 4,
) -> str:
    """
    Generate a collision-resistant ID.

    Format: {prefix}-{hash} (e.g., feat-a1b2c3d4)

    The hash is derived from:
    - Title (for some content-addressability)
    - Timestamp (microsecond precision in UTC)
    - Random bytes (entropy)

    Args:
        node_type: Type of node (feature, bug, chore, etc.)
        title: Node title (used in hash for content-addressability)
        entropy_bytes: Number of random bytes to include (default 4)

    Returns:
        A collision-resistant ID like "feat-a1b2c3d4"

    Example:
        >>> generate_id("feature", "User Authentication")
        'feat-7f3a2b1c'
        >>> generate_id("bug", "Login fails on Safari")
        'bug-9e8d7c6b'
    """
    prefix = PREFIXES.get(node_type, node_type[:4].lower())

    # Combine multiple sources of uniqueness
    timestamp = datetime.now(timezone.utc).isoformat()
    random_bytes = os.urandom(entropy_bytes)

    # Create hash from all sources
    content = f"{title}:{timestamp}".encode() + random_bytes
    hash_digest = hashlib.sha256(content).hexdigest()[:8]

    return f"{prefix}-{hash_digest}"


def generate_hierarchical_id(
    parent_id: str,
    index: int | None = None,
) -> str:
    """
    Generate a sub-task ID under a parent.

    Format: {parent_id}.{index} (e.g., feat-a1b2c3d4.1)

    If index is not provided, it auto-increments based on
    existing siblings (requires filesystem check).

    Args:
        parent_id: The parent node's ID
        index: Sub-task index (1-based). Auto-assigned if None.

    Returns:
        A hierarchical ID like "feat-a1b2c3d4.1" or "feat-a1b2c3d4.1.2"

    Example:
        >>> generate_hierarchical_id("feat-a1b2c3d4", 1)
        'feat-a1b2c3d4.1'
        >>> generate_hierarchical_id("feat-a1b2c3d4.1", 2)
        'feat-a1b2c3d4.1.2'
    """
    if index is None:
        raise ValueError("index is required (auto-increment not yet implemented)")

    if index < 1:
        raise ValueError("index must be >= 1")

    return f"{parent_id}.{index}"


def parse_id(node_id: str) -> dict[str, str | int | list[int] | None]:
    """
    Parse an ID into its components.

    Args:
        node_id: The ID to parse

    Returns:
        Dictionary with:
        - prefix: The type prefix (e.g., "feat")
        - node_type: The full node type (e.g., "feature")
        - hash: The hash portion (e.g., "a1b2c3d4")
        - hierarchy: List of sub-indices (e.g., [1, 2] for ".1.2")
        - is_legacy: Whether this is an old-format ID

    Example:
        >>> parse_id("feat-a1b2c3d4.1.2")
        {
            'prefix': 'feat',
            'node_type': 'feature',
            'hash': 'a1b2c3d4',
            'hierarchy': [1, 2],
            'is_legacy': False
        }
    """
    # Try new hash-based format
    match = HASH_ID_PATTERN.match(node_id)
    if match:
        prefix = match.group(1)
        hash_part = match.group(2)

        # Extract hierarchy by finding all .N segments after the hash
        # The regex captures the last one, but we need all of them
        hierarchy = []
        base_id = f"{prefix}-{hash_part}"
        if len(node_id) > len(base_id):
            hierarchy_str = node_id[len(base_id) :]  # e.g., ".1.2"
            hierarchy = [int(x) for x in hierarchy_str.split(".") if x]

        return {
            "prefix": prefix,
            "node_type": PREFIX_TO_TYPE.get(prefix, prefix),
            "hash": hash_part,
            "hierarchy": hierarchy,
            "is_legacy": False,
        }

    # Try legacy format (feature-20241222-143022)
    legacy_match = LEGACY_ID_PATTERN.match(node_id)
    if legacy_match:
        prefix = legacy_match.group(1)
        timestamp = legacy_match.group(2)

        return {
            "prefix": prefix,
            "node_type": prefix,  # Legacy uses full type as prefix
            "hash": timestamp,
            "hierarchy": [],
            "is_legacy": True,
        }

    # Unknown format
    return {
        "prefix": None,
        "node_type": None,
        "hash": None,
        "hierarchy": [],
        "is_legacy": None,
    }


def is_valid_id(node_id: str) -> bool:
    """
    Check if an ID is valid (either new or legacy format).

    Args:
        node_id: The ID to validate

    Returns:
        True if the ID matches a known format

    Example:
        >>> is_valid_id("feat-a1b2c3d4")
        True
        >>> is_valid_id("feat-a1b2c3d4.1.2")
        True
        >>> is_valid_id("feature-20241222-143022")
        True
        >>> is_valid_id("invalid")
        False
    """
    return bool(HASH_ID_PATTERN.match(node_id) or LEGACY_ID_PATTERN.match(node_id))


def is_legacy_id(node_id: str) -> bool:
    """
    Check if an ID uses the legacy timestamp format.

    Args:
        node_id: The ID to check

    Returns:
        True if this is a legacy format ID (e.g., feature-20241222-143022)

    Example:
        >>> is_legacy_id("feature-20241222-143022")
        True
        >>> is_legacy_id("feat-a1b2c3d4")
        False
    """
    return bool(LEGACY_ID_PATTERN.match(node_id))


def get_parent_id(node_id: str) -> str | None:
    """
    Get the parent ID for a hierarchical ID.

    Args:
        node_id: A hierarchical ID like "feat-a1b2c3d4.1.2"

    Returns:
        The parent ID ("feat-a1b2c3d4.1") or None if not hierarchical

    Example:
        >>> get_parent_id("feat-a1b2c3d4.1.2")
        'feat-a1b2c3d4.1'
        >>> get_parent_id("feat-a1b2c3d4.1")
        'feat-a1b2c3d4'
        >>> get_parent_id("feat-a1b2c3d4")
        None
    """
    if "." not in node_id:
        return None

    return node_id.rsplit(".", 1)[0]


def get_root_id(node_id: str) -> str:
    """
    Get the root ID (without hierarchy) for any ID.

    Args:
        node_id: Any ID, possibly hierarchical

    Returns:
        The root ID without hierarchy portion

    Example:
        >>> get_root_id("feat-a1b2c3d4.1.2")
        'feat-a1b2c3d4'
        >>> get_root_id("feat-a1b2c3d4")
        'feat-a1b2c3d4'
    """
    parsed = parse_id(node_id)
    if parsed["prefix"] and parsed["hash"]:
        return f"{parsed['prefix']}-{parsed['hash']}"
    return node_id.split(".")[0]


def get_depth(node_id: str) -> int:
    """
    Get the hierarchy depth of an ID.

    Args:
        node_id: Any ID

    Returns:
        0 for root IDs, 1+ for hierarchical IDs

    Example:
        >>> get_depth("feat-a1b2c3d4")
        0
        >>> get_depth("feat-a1b2c3d4.1")
        1
        >>> get_depth("feat-a1b2c3d4.1.2")
        2
    """
    parsed = parse_id(node_id)
    hierarchy = parsed.get("hierarchy", [])
    if isinstance(hierarchy, list):
        return len(hierarchy)
    return 0
