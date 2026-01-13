"""Decorators for function enhancement and cross-cutting concerns.

This module provides decorators for common patterns like retry logic with
exponential backoff, caching, timing, and error handling.
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    """Raised when a function exhausts all retry attempts."""

    def __init__(
        self,
        function_name: str,
        attempts: int,
        last_exception: Exception,
    ):
        self.function_name = function_name
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Function '{function_name}' failed after {attempts} attempts. "
            f"Last error: {last_exception}"
        )


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator adding retry logic with exponential backoff to any function.

    Implements exponential backoff with optional jitter to gracefully handle
    transient failures. Useful for I/O operations, API calls, and distributed
    system interactions.

    Args:
        max_attempts: Maximum number of attempts (default: 3). Must be >= 1.
        initial_delay: Initial delay in seconds before first retry (default: 1.0).
            Must be >= 0.
        max_delay: Maximum delay in seconds between retries (default: 60.0).
            Caps the exponential backoff. Must be >= initial_delay.
        exponential_base: Base for exponential backoff calculation (default: 2.0).
            delay = min(initial_delay * (base ** attempt_number), max_delay)
        jitter: Whether to add random jitter to delays (default: True).
            Helps prevent thundering herd problem in distributed systems.
        exceptions: Tuple of exception types to catch and retry on
            (default: (Exception,)). Other exceptions propagate immediately.
        on_retry: Optional callback invoked on each retry with signature:
            on_retry(attempt_number, exception, delay_seconds).
            Useful for logging, metrics, or custom backoff strategies.

    Returns:
        Decorated function that retries on specified exceptions.

    Raises:
        RetryError: If all retry attempts are exhausted.
        Other exceptions: If exception type is not in the retry list.

    Examples:
        Basic retry with default parameters:
        >>> @retry()
        ... def unstable_api_call():
        ...     response = requests.get('https://api.example.com/data')
        ...     response.raise_for_status()
        ...     return response.json()

        Retry with custom parameters:
        >>> @retry(
        ...     max_attempts=5,
        ...     initial_delay=0.5,
        ...     max_delay=30.0,
        ...     exponential_base=1.5,
        ...     exceptions=(ConnectionError, TimeoutError),
        ... )
        ... def fetch_with_timeout():
        ...     return expensive_io_operation()

        With custom retry callback for logging:
        >>> def log_retry(attempt, exc, delay):
        ...     logger.warning(
        ...         f"Retry attempt {attempt} after {delay}s: {exc}"
        ...     )
        >>> @retry(
        ...     max_attempts=3,
        ...     on_retry=log_retry,
        ...     exceptions=(IOError,),
        ... )
        ... def read_file(path):
        ...     with open(path) as f:
        ...         return f.read()

        Retry only specific exceptions (fail fast for others):
        >>> @retry(
        ...     max_attempts=3,
        ...     exceptions=(ConnectionError, TimeoutError),
        ... )
        ... def resilient_request(url):
        ...     # Will retry on connection errors but fail immediately on 404
        ...     return requests.get(url, timeout=5).json()

        Using with async functions:
        >>> import asyncio
        >>> @retry(max_attempts=3, initial_delay=0.1)
        ... async def async_api_call():
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get('https://api.example.com') as resp:
        ...             return await resp.json()
        >>> asyncio.run(async_api_call())

    Backoff Calculation:
        The delay before retry N is calculated as:
        - exponential: initial_delay * (exponential_base ** (attempt - 1))
        - capped: min(exponential, max_delay)
        - jittered: delay * (0.5 + random(0.0, 1.0)) if jitter=True

        Example with exponential_base=2.0, initial_delay=1.0, max_delay=60.0:
        - Attempt 1 fails, retry after: 1s
        - Attempt 2 fails, retry after: 2s
        - Attempt 3 fails, retry after: 4s
        - Attempt 4 fails, retry after: 8s
        - Attempt 5 fails, retry after: 16s
        - Attempt 6 fails, retry after: 32s
        - Attempt 7 fails, raise RetryError (max_attempts=3 means 3 total attempts)

    Notes:
        - If max_attempts=1, no retries occur (function runs once)
        - Jitter is uniformly distributed in range [0.5 * delay, 1.5 * delay]
        - Callbacks (on_retry) are invoked BEFORE sleeping, not after
        - Thread-safe but not async-safe without adaptation
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if initial_delay < 0:
        raise ValueError("initial_delay must be >= 0")
    if max_delay < initial_delay:
        raise ValueError("max_delay must be >= initial_delay")
    if exponential_base <= 0:
        raise ValueError("exponential_base must be > 0")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        # Last attempt failed, raise RetryError
                        raise RetryError(
                            function_name=func.__name__,
                            attempts=max_attempts,
                            last_exception=e,
                        ) from e

                    # Calculate backoff with exponential growth and jitter
                    exponential_delay = initial_delay * (
                        exponential_base ** (attempt - 1)
                    )
                    delay = min(exponential_delay, max_delay)

                    if jitter:
                        # Add jitter: multiply by random value in [0.5, 1.5]
                        delay *= 0.5 + random.random()

                    # Invoke callback before sleeping
                    if on_retry is not None:
                        on_retry(attempt, e, delay)
                    else:
                        logger.debug(
                            f"Retry attempt {attempt}/{max_attempts} for "
                            f"{func.__name__} after {delay:.2f}s: {e}"
                        )

                    time.sleep(delay)

            # This should never be reached, but satisfy type checker
            assert last_exception is not None
            raise RetryError(
                function_name=func.__name__,
                attempts=max_attempts,
                last_exception=last_exception,
            )

        return wrapper

    return decorator


def retry_async(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Async version of retry decorator with exponential backoff.

    Identical to retry() but uses asyncio.sleep instead of time.sleep,
    allowing it to be used with async/await functions without blocking.

    Args:
        max_attempts: Maximum number of attempts (default: 3). Must be >= 1.
        initial_delay: Initial delay in seconds before first retry (default: 1.0).
        max_delay: Maximum delay in seconds between retries (default: 60.0).
        exponential_base: Base for exponential backoff (default: 2.0).
        jitter: Whether to add random jitter to delays (default: True).
        exceptions: Tuple of exception types to catch and retry on.
        on_retry: Optional callback invoked on each retry.

    Returns:
        Decorated async function that retries on specified exceptions.

    Raises:
        RetryError: If all retry attempts are exhausted.

    Examples:
        >>> import asyncio
        >>> @retry_async(max_attempts=3)
        ... async def fetch_data():
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get('https://api.example.com') as resp:
        ...             return await resp.json()

        >>> @retry_async(
        ...     max_attempts=5,
        ...     initial_delay=0.1,
        ...     exceptions=(asyncio.TimeoutError, ConnectionError),
        ... )
        ... async def resilient_query():
        ...     return await db.query("SELECT * FROM users")
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if initial_delay < 0:
        raise ValueError("initial_delay must be >= 0")
    if max_delay < initial_delay:
        raise ValueError("max_delay must be >= initial_delay")
    if exponential_base <= 0:
        raise ValueError("exponential_base must be > 0")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio

            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        raise RetryError(
                            function_name=func.__name__,
                            attempts=max_attempts,
                            last_exception=e,
                        ) from e

                    exponential_delay = initial_delay * (
                        exponential_base ** (attempt - 1)
                    )
                    delay = min(exponential_delay, max_delay)

                    if jitter:
                        delay *= 0.5 + random.random()

                    if on_retry is not None:
                        on_retry(attempt, e, delay)
                    else:
                        logger.debug(
                            f"Retry attempt {attempt}/{max_attempts} for "
                            f"{func.__name__} after {delay:.2f}s: {e}"
                        )

                    await asyncio.sleep(delay)

            assert last_exception is not None
            raise RetryError(
                function_name=func.__name__,
                attempts=max_attempts,
                last_exception=last_exception,
            )

        return wrapper

    return decorator


__all__ = [
    "retry",
    "retry_async",
    "RetryError",
]
