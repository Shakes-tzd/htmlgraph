"""
Auto-help system for SDK operations.

Provides automatic help display when SDK operations fail,
showing relevant documentation for the failed operation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

logger = logging.getLogger(__name__)


def get_help_for_exception(sdk: SDK, exception: Exception, context: str = "") -> str:
    """
    Generate helpful error message with SDK documentation.

    Args:
        sdk: SDK instance to get help from
        exception: The exception that was raised
        context: Context string (e.g., "features.create", "bugs.where")

    Returns:
        Formatted help text with error and relevant documentation
    """
    # Extract topic from context (e.g., "features" from "features.create")
    topic = context.split(".")[0] if "." in context else context

    # Get base error message
    error_msg = str(exception)

    # Get relevant help
    help_text = ""
    if topic:
        try:
            help_text = sdk.help(topic)
        except Exception:
            # Fallback to general help if topic-specific help fails
            help_text = sdk.help()

    # Format combined message
    output = f"""
❌ SDK Operation Failed: {error_msg}

{"=" * 60}
📚 RELEVANT DOCUMENTATION
{"=" * 60}

{help_text}

💡 TIP: Use sdk.help('{topic}') for more details on this collection.
"""
    return output


def show_help_on_error(sdk: SDK, exception: Exception, context: str = "") -> None:
    """
    Display help message for exception to stderr.

    Args:
        sdk: SDK instance
        exception: The exception that occurred
        context: Context string for the operation
    """
    help_msg = get_help_for_exception(sdk, exception, context)
    # Use logger to output to stderr (configured with Rich in __init__.py)
    logger.error(help_msg)


class AutoHelpWrapper:
    """
    Wrapper for collection methods that automatically shows help on errors.

    This wrapper catches exceptions from collection operations and displays
    relevant SDK documentation to help users understand what went wrong.
    """

    def __init__(self, sdk: SDK, collection_name: str):
        """
        Initialize wrapper.

        Args:
            sdk: Parent SDK instance
            collection_name: Name of the collection (e.g., "features", "bugs")
        """
        self._sdk = sdk
        self._collection_name = collection_name

    def wrap_method(self, method: Any, method_name: str) -> Any:
        """
        Wrap a method to show help on exceptions.

        Args:
            method: The method to wrap
            method_name: Name of the method

        Returns:
            Wrapped method
        """

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return method(*args, **kwargs)
            except Exception as e:
                # Show help automatically
                context = f"{self._collection_name}.{method_name}"
                show_help_on_error(self._sdk, e, context)
                # Re-raise the original exception
                raise

        return wrapped


def enable_auto_help(sdk: SDK) -> None:
    """
    Enable auto-help for all SDK collections.

    This wraps common collection methods to automatically show help on errors.

    Args:
        sdk: SDK instance to enable auto-help for
    """
    # Collections to wrap
    collections = [
        "features",
        "bugs",
        "spikes",
        "chores",
        "epics",
        "phases",
        "tracks",
        "sessions",
        "patterns",
        "insights",
        "metrics",
        "todos",
    ]

    # Methods to wrap (common operations that might fail)
    methods_to_wrap = [
        "create",
        "get",
        "edit",
        "where",
        "claim",
        "release",
        "mark_done",
        "assign",
        "batch_update",
        "batch_delete",
    ]

    for collection_name in collections:
        if not hasattr(sdk, collection_name):
            continue

        collection = getattr(sdk, collection_name)
        wrapper = AutoHelpWrapper(sdk, collection_name)

        for method_name in methods_to_wrap:
            if not hasattr(collection, method_name):
                continue

            original_method = getattr(collection, method_name)
            wrapped_method = wrapper.wrap_method(original_method, method_name)

            # Store original method for testing
            setattr(collection, f"_{method_name}_original", original_method)
            # Replace with wrapped version
            setattr(collection, method_name, wrapped_method)


__all__ = [
    "get_help_for_exception",
    "show_help_on_error",
    "AutoHelpWrapper",
    "enable_auto_help",
]
