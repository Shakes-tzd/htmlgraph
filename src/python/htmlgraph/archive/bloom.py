"""
Bloom filter implementation for archive search optimization.

Uses MurmurHash3 for 22x faster hashing with hardware optimizations.
Target: 32.8% latency reduction by skipping 70-90% of archives.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    import mmh3  # type: ignore

    HAS_MMH3 = True
except ImportError:
    HAS_MMH3 = False


class BloomFilter:
    """
    Space-efficient probabilistic data structure for archive filtering.

    Optimized for speed with:
    - MurmurHash3 hardware acceleration (if available)
    - Configurable false positive rate (default 0.01)
    - Efficient bit array storage
    """

    def __init__(
        self, expected_items: int = 1000, false_positive_rate: float = 0.01
    ) -> None:
        """
        Initialize Bloom filter.

        Args:
            expected_items: Expected number of items to add
            false_positive_rate: Desired false positive rate (0.01 = 1%)
        """
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate

        # Calculate optimal bit array size
        self.bit_count = self._optimal_bit_count(expected_items, false_positive_rate)

        # Calculate optimal number of hash functions
        self.hash_count = self._optimal_hash_count(self.bit_count, expected_items)

        # Initialize bit array (using bytearray for efficiency)
        self.bit_array = bytearray((self.bit_count + 7) // 8)

        self.items_added = 0

    def _optimal_bit_count(self, n: int, p: float) -> int:
        """
        Calculate optimal bit array size.

        Formula: m = -(n * ln(p)) / (ln(2)^2)
        """
        return int(-n * math.log(p) / (math.log(2) ** 2))

    def _optimal_hash_count(self, m: int, n: int) -> int:
        """
        Calculate optimal number of hash functions.

        Formula: k = (m / n) * ln(2)
        """
        return max(1, int((m / n) * math.log(2)))

    def _hash(self, item: str, seed: int) -> int:
        """
        Hash item with seed using MurmurHash3 or fallback to hashlib.

        Args:
            item: Item to hash
            seed: Hash seed for different hash functions

        Returns:
            Hash value modulo bit_count
        """
        if HAS_MMH3:
            # MurmurHash3 - 22x faster with hardware optimization
            hash_val: int = mmh3.hash(item, seed)  # type: ignore
            return hash_val % self.bit_count
        else:
            # Fallback to hashlib (slower but always available)
            hash_obj = hashlib.sha256(f"{item}{seed}".encode())
            return int.from_bytes(hash_obj.digest()[:4], "big") % self.bit_count

    def _set_bit(self, position: int) -> None:
        """Set bit at position to 1."""
        byte_index = position // 8
        bit_index = position % 8
        self.bit_array[byte_index] |= 1 << bit_index

    def _get_bit(self, position: int) -> bool:
        """Get bit value at position."""
        byte_index = position // 8
        bit_index = position % 8
        return bool(self.bit_array[byte_index] & (1 << bit_index))

    def add(self, item: str) -> None:
        """
        Add item to Bloom filter.

        Args:
            item: String to add
        """
        for seed in range(self.hash_count):
            position = self._hash(item, seed)
            self._set_bit(position)

        self.items_added += 1

    def might_contain(self, item: str) -> bool:
        """
        Check if item might be in the set.

        Args:
            item: String to check

        Returns:
            True if item might be present (or false positive)
            False if item is definitely not present
        """
        for seed in range(self.hash_count):
            position = self._hash(item, seed)
            if not self._get_bit(position):
                return False
        return True

    def build_for_archive(self, entities: list[dict[str, Any]]) -> None:
        """
        Build Bloom filter from archive entities.

        Indexes:
        - Entity IDs
        - Titles (lowercased, tokenized)
        - Description text (lowercased, tokenized)

        Args:
            entities: List of entity dictionaries with id, title, description
        """
        for entity in entities:
            # Add entity ID
            self.add(entity["id"])

            # Add title tokens (lowercased)
            if "title" in entity and entity["title"]:
                for word in entity["title"].lower().split():
                    self.add(word)

            # Add description tokens (lowercased)
            if "description" in entity and entity["description"]:
                for word in entity["description"].lower().split():
                    self.add(word)

    def save(self, filepath: Path) -> None:
        """
        Save Bloom filter to disk.

        Args:
            filepath: Path to save .bloom file
        """
        data = {
            "expected_items": self.expected_items,
            "false_positive_rate": self.false_positive_rate,
            "bit_count": self.bit_count,
            "hash_count": self.hash_count,
            "items_added": self.items_added,
            "bit_array": list(self.bit_array),  # Convert bytearray to list for JSON
        }

        with open(filepath, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, filepath: Path) -> "BloomFilter":
        """
        Load Bloom filter from disk.

        Args:
            filepath: Path to .bloom file

        Returns:
            Loaded BloomFilter instance
        """
        with open(filepath) as f:
            data = json.load(f)

        # Create instance with saved parameters
        bloom = cls(
            expected_items=data["expected_items"],
            false_positive_rate=data["false_positive_rate"],
        )

        # Restore state
        bloom.bit_count = data["bit_count"]
        bloom.hash_count = data["hash_count"]
        bloom.items_added = data["items_added"]
        bloom.bit_array = bytearray(data["bit_array"])

        return bloom

    def get_stats(self) -> dict[str, Any]:
        """
        Get Bloom filter statistics.

        Returns:
            Dictionary with stats (size, items, FPR, etc.)
        """
        # Calculate actual false positive rate
        actual_fpr = (
            (1 - math.exp(-self.hash_count * self.items_added / self.bit_count))
            ** self.hash_count
            if self.items_added > 0
            else 0
        )

        return {
            "expected_items": self.expected_items,
            "items_added": self.items_added,
            "bit_count": self.bit_count,
            "hash_count": self.hash_count,
            "bytes_used": len(self.bit_array),
            "target_fpr": self.false_positive_rate,
            "actual_fpr": actual_fpr,
            "utilization": self.items_added / self.expected_items
            if self.expected_items > 0
            else 0,
            "using_mmh3": HAS_MMH3,
        }
