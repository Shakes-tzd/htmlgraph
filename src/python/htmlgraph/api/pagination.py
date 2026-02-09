"""
Pagination Helper - Standardized offset/limit pagination across all list endpoints.

Provides:
- Pagination metadata (total_count, page, page_size, has_next, has_prev)
- Standard response wrapper
- Query building helpers
- Consistent pagination across all APIs
"""

import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PaginationMetadata:
    """Pagination metadata included in all list responses."""

    total_count: int
    offset: int
    limit: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert pagination metadata to dictionary."""
        return {
            "total_count": self.total_count,
            "offset": self.offset,
            "limit": self.limit,
            "page": self.page,
            "page_size": self.page_size,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


@dataclass
class PaginatedResponse(Generic[T]):
    """Standard paginated response wrapper."""

    items: list[T]
    pagination: PaginationMetadata

    def to_dict(self) -> dict[str, Any]:
        """Convert paginated response to dictionary."""
        return {
            "items": self.items,
            "pagination": self.pagination.to_dict(),
        }


def calculate_pagination_metadata(
    total_count: int, offset: int, limit: int
) -> PaginationMetadata:
    """
    Calculate pagination metadata for a query result.

    Args:
        total_count: Total number of items in the collection
        offset: Current offset (0-indexed)
        limit: Items per page

    Returns:
        PaginationMetadata with all pagination information
    """
    page = (offset // limit) + 1 if limit > 0 else 1
    has_next = (offset + limit) < total_count
    has_prev = offset > 0

    return PaginationMetadata(
        total_count=total_count,
        offset=offset,
        limit=limit,
        page=page,
        page_size=limit,
        has_next=has_next,
        has_prev=has_prev,
    )


class PaginationHelper:
    """Helper class for building paginated queries and responses."""

    @staticmethod
    def validate_pagination_params(offset: int, limit: int) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters.

        Args:
            offset: Requested offset (0-indexed)
            limit: Requested limit (items per page)

        Returns:
            Tuple of (validated_offset, validated_limit)

        Raises:
            ValueError: If parameters are invalid
        """
        # Ensure offset is non-negative
        if offset < 0:
            logger.warning(f"Invalid offset {offset}, using 0")
            offset = 0

        # Ensure limit is between 1 and 500 (max 500 items per page)
        if limit < 1:
            logger.warning(f"Invalid limit {limit}, using 10")
            limit = 10
        elif limit > 500:
            logger.warning(f"Limit {limit} exceeds maximum 500, capping at 500")
            limit = 500

        return offset, limit

    @staticmethod
    def build_pagination_clause(offset: int, limit: int) -> str:
        """
        Build SQL LIMIT/OFFSET clause.

        Args:
            offset: Number of rows to skip
            limit: Maximum number of rows to return

        Returns:
            SQL clause string "LIMIT ? OFFSET ?"
        """
        return "LIMIT ? OFFSET ?"

    @staticmethod
    def get_pagination_params(offset: int, limit: int) -> list[Any]:
        """
        Get parameters for pagination SQL clause.

        Args:
            offset: Number of rows to skip
            limit: Maximum number of rows to return

        Returns:
            List of parameters [limit, offset] for SQL query
        """
        return [limit, offset]

    @staticmethod
    def create_paginated_response(
        items: list[T], total_count: int, offset: int, limit: int
    ) -> dict[str, Any]:
        """
        Create a paginated response with metadata.

        Args:
            items: List of items for this page
            total_count: Total items in collection
            offset: Current offset
            limit: Items per page

        Returns:
            Dictionary with items and pagination metadata
        """
        pagination = calculate_pagination_metadata(total_count, offset, limit)
        return {
            "items": items,
            "pagination": pagination.to_dict(),
        }
