"""
Services package for SessionManager functionality decomposition.

This package contains service classes that handle specific domains of functionality
previously embedded in the SessionManager god object.
"""

from .claiming import ClaimingService

__all__ = ["ClaimingService"]
