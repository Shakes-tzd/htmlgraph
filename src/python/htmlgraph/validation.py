"""
Rich CLI validation error formatting and utilities.

Provides beautiful error display for Pydantic validation failures.
"""

from collections.abc import Callable
from typing import TypeVar

from pydantic import ValidationError
from rich.console import Console

console = Console()

T = TypeVar("T")


def display_validation_error(error: ValidationError) -> None:
    """
    Display a Pydantic validation error in Rich format.

    Args:
        error: ValidationError from Pydantic model validation

    Example:
        try:
            input_data = FeatureCreateInput(title="", priority="invalid")
        except ValidationError as e:
            display_validation_error(e)
    """
    console.print("[red]✗ Validation Error[/red]")
    console.print()

    for err in error.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        error_type = err["type"]

        # Color code by error type for better UX
        if "at least" in msg.lower() or "at most" in msg.lower():
            # Length/range constraint violation
            console.print(f"  [yellow]{field}:[/yellow] {msg}")
        elif "must be" in msg.lower() or "is not valid" in msg.lower():
            # Type/value constraint violation
            console.print(f"  [cyan]{field}:[/cyan] {msg}")
        elif error_type == "string_pattern":
            # Pattern validation failed
            console.print(f"  [magenta]{field}:[/magenta] {msg}")
        else:
            # Generic validation error
            console.print(f"  [red]{field}:[/red] {msg}")

    console.print()


def validate_input(
    validator_class: type[T],
    **kwargs: object,
) -> T | None:
    """
    Validate input and display rich error messages on failure.

    Args:
        validator_class: Pydantic model class to validate against
        **kwargs: Input data to validate

    Returns:
        Validated model instance, or None if validation failed

    Example:
        input_data = validate_input(FeatureCreateInput, title="My Feature", priority="high")
        if input_data is None:
            sys.exit(1)
        # Use input_data.title, input_data.priority, etc.
    """
    try:
        return validator_class(**kwargs)
    except ValidationError as e:
        display_validation_error(e)
        return None


def wrap_command_validation(func: Callable[..., None]) -> Callable[..., None]:
    """
    Decorator to wrap CLI command functions with validation error handling.

    This decorator catches ValidationError and displays it in Rich format,
    then exits gracefully.

    Args:
        func: CLI command function

    Returns:
        Wrapped function with validation error handling

    Example:
        @wrap_command_validation
        def cmd_feature_create(args: argparse.Namespace) -> None:
            input_data = FeatureCreateInput(
                title=args.title,
                priority=args.priority
            )
            # Rest of command logic
    """

    def wrapper(*args: object, **kwargs: object) -> None:
        import sys

        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            display_validation_error(e)
            sys.exit(1)

    return wrapper
