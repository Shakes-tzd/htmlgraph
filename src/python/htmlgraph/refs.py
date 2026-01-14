from __future__ import annotations

"""
Short reference manager for graph nodes.

Manages persistent mapping of short refs (@f1, @t2, @b5) to full node IDs,
enabling AI-friendly snapshots and queries.
"""


import json
from datetime import datetime
from pathlib import Path


class RefManager:
    """
    Manages short references (@f1, @t1, @b5, etc.) for graph nodes.

    Maintains a persistent refs.json file mapping short refs to full node IDs.
    Refs are stable across sessions and auto-generated on first access.

    Ref format: @{prefix}{number}
    Prefixes: f=feature, t=track, b=bug, s=spike, c=chore, e=epic, d=todo

    Example:
        >>> ref_mgr = RefManager(Path(".htmlgraph"))
        >>> ref = ref_mgr.generate_ref("feat-a1b2c3d4")
        >>> print(ref)  # "@f1"
        >>> full_id = ref_mgr.resolve_ref("@f1")
        >>> print(full_id)  # "feat-a1b2c3d4"
    """

    # Map node ID prefix to short ref prefix
    PREFIX_MAP = {
        "feat": "f",
        "trk": "t",
        "bug": "b",
        "spk": "s",
        "chr": "c",
        "epc": "e",
        "todo": "d",
        "phs": "p",
    }

    # Reverse mapping for type lookup
    TYPE_MAP = {
        "f": "feature",
        "t": "track",
        "b": "bug",
        "s": "spike",
        "c": "chore",
        "e": "epic",
        "d": "todo",
        "p": "phase",
    }

    def __init__(self, graph_dir: Path):
        """
        Initialize RefManager.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.refs_file = self.graph_dir / "refs.json"
        self._refs: dict[str, str] = {}  # Maps: "@f1" -> "feat-a1b2c3d4"
        self._reverse_refs: dict[str, str] = {}  # Maps: "feat-a1b2c3d4" -> "@f1"
        self._load()

    def _load(self) -> None:
        """Load refs.json into memory."""
        if not self.refs_file.exists():
            self._refs = {}
            self._reverse_refs = {}
            return

        try:
            with open(self.refs_file, encoding="utf-8") as f:
                data = json.load(f)
                self._refs = data.get("refs", {})

            # Build reverse mapping
            self._reverse_refs = {v: k for k, v in self._refs.items()}
        except (json.JSONDecodeError, OSError) as e:
            # Corrupted file - start fresh
            import logging

            logging.warning(f"Failed to load refs.json: {e}. Starting fresh.")
            self._refs = {}
            self._reverse_refs = {}

    def _save(self) -> None:
        """Save refs to refs.json."""
        # Ensure directory exists
        self.graph_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "refs": self._refs,
            "version": 1,
            "regenerated_at": datetime.now().isoformat(),
        }

        try:
            with open(self.refs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            import logging

            logging.error(f"Failed to save refs.json: {e}")

    def _parse_node_type(self, node_id: str) -> str | None:
        """
        Extract node type prefix from node ID.

        Args:
            node_id: Full node ID like "feat-a1b2c3d4"

        Returns:
            Node type prefix (e.g., "feat") or None if invalid
        """
        if "-" not in node_id:
            return None

        prefix = node_id.split("-", 1)[0]
        return prefix if prefix in self.PREFIX_MAP else None

    def _next_ref_number(self, prefix: str) -> int:
        """
        Get next available ref number for a type.

        Args:
            prefix: Short ref prefix (e.g., "f", "t", "b")

        Returns:
            Next available number (1, 2, 3, ...)
        """
        # Find all refs with this prefix
        existing = [int(ref[2:]) for ref in self._refs if ref.startswith(f"@{prefix}")]
        return max(existing, default=0) + 1

    def generate_ref(self, node_id: str) -> str:
        """
        Generate a short ref for a node ID.

        This method is idempotent - calling it multiple times with the same
        node_id returns the same ref without creating duplicates.

        Args:
            node_id: Full node ID like "feat-a1b2c3d4"

        Returns:
            Short ref like "@f1"

        Raises:
            ValueError: If node_id has invalid format

        Example:
            >>> ref = ref_mgr.generate_ref("feat-abc123")
            >>> print(ref)  # "@f1"
            >>> # Second call returns same ref
            >>> ref2 = ref_mgr.generate_ref("feat-abc123")
            >>> assert ref == ref2
        """
        # Check if already has ref (idempotent)
        if node_id in self._reverse_refs:
            return self._reverse_refs[node_id]

        # Parse node type
        node_prefix = self._parse_node_type(node_id)
        if not node_prefix:
            raise ValueError(f"Invalid node ID format: {node_id}")

        # Get short prefix
        short_prefix = self.PREFIX_MAP[node_prefix]

        # Generate next ref
        number = self._next_ref_number(short_prefix)
        short_ref = f"@{short_prefix}{number}"

        # Store mappings
        self._refs[short_ref] = node_id
        self._reverse_refs[node_id] = short_ref

        # Persist
        self._save()

        return short_ref

    def get_ref(self, node_id: str) -> str | None:
        """
        Get existing ref for a node ID (create if not exist).

        Args:
            node_id: Full node ID like "feat-a1b2c3d4"

        Returns:
            Short ref like "@f1", or None if node_id invalid

        Example:
            >>> ref = ref_mgr.get_ref("feat-abc123")
            >>> # Creates ref if doesn't exist
        """
        # Return existing ref
        if node_id in self._reverse_refs:
            return self._reverse_refs[node_id]

        # Generate new ref if valid node ID
        try:
            return self.generate_ref(node_id)
        except ValueError:
            return None

    def resolve_ref(self, short_ref: str) -> str | None:
        """
        Resolve short ref to full node ID.

        Args:
            short_ref: "@f1", "@t2", etc.

        Returns:
            Full node ID or None if not found

        Example:
            >>> full_id = ref_mgr.resolve_ref("@f1")
            >>> print(full_id)  # "feat-abc123"
        """
        return self._refs.get(short_ref)

    def get_all_refs(self) -> dict[str, str]:
        """
        Return all refs.

        Returns:
            Dict mapping short refs to full IDs: {"@f1": "feat-a1b2c3d4", ...}
        """
        return self._refs.copy()

    def get_refs_by_type(self, node_type: str) -> list[tuple[str, str]]:
        """
        Get all refs for a specific type.

        Args:
            node_type: "feature", "track", "bug", "spike", "chore", "epic", "todo", "phase"

        Returns:
            List of (short_ref, full_id) tuples sorted by ref number

        Example:
            >>> feature_refs = ref_mgr.get_refs_by_type("feature")
            >>> for ref, full_id in feature_refs:
            ...     print(f"{ref} -> {full_id}")
        """
        # Get prefix for this type
        prefix = None
        for short_prefix, type_name in self.TYPE_MAP.items():
            if type_name == node_type:
                prefix = short_prefix
                break

        if not prefix:
            return []

        # Filter refs by prefix
        matching = [
            (ref, full_id)
            for ref, full_id in self._refs.items()
            if ref.startswith(f"@{prefix}")
        ]

        # Sort by ref number
        def sort_key(item: tuple[str, str]) -> int:
            ref = item[0]
            try:
                return int(ref[2:])  # Extract number after "@f"
            except (ValueError, IndexError):
                return 0

        return sorted(matching, key=sort_key)

    def rebuild_refs(self) -> None:
        """
        Rebuild refs from all .htmlgraph/ files (recovery tool).

        Scans all collection directories (features/, tracks/, bugs/, etc.)
        and rebuilds refs.json from scratch. Preserves existing refs where
        possible to maintain stability.

        This is a recovery tool for when refs.json is corrupted or deleted.

        Example:
            >>> ref_mgr.rebuild_refs()
            >>> # Refs regenerated from file system
        """
        # Save current refs for preservation
        old_refs = self._refs.copy()

        # Clear in-memory refs
        self._refs = {}
        self._reverse_refs = {}

        # Scan all collection directories
        collections = [
            "features",
            "tracks",
            "bugs",
            "spikes",
            "chores",
            "epics",
            "todos",
            "phases",
        ]

        for collection in collections:
            collection_dir = self.graph_dir / collection
            if not collection_dir.exists():
                continue

            # Scan HTML files
            for html_file in collection_dir.glob("*.html"):
                # Extract node ID from filename (without .html)
                node_id = html_file.stem

                # Skip if invalid format
                if not self._parse_node_type(node_id):
                    continue

                # Try to preserve existing ref
                if node_id in {v for v in old_refs.values()}:
                    # Find old ref
                    old_ref = next(
                        (k for k, v in old_refs.items() if v == node_id), None
                    )
                    if old_ref:
                        # Preserve old ref
                        self._refs[old_ref] = node_id
                        self._reverse_refs[node_id] = old_ref
                        continue

                # Generate new ref
                self.generate_ref(node_id)

        # Save to disk
        self._save()
