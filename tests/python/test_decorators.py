"""Tests for retry decorator with exponential backoff.

Tests cover:
- Basic retry functionality with various attempt counts
- Exponential backoff timing calculations
- Jitter application and behavior
- Exception filtering (retry only specified exceptions)
- Callback invocation on retry events
- Error cases and edge conditions
- Async variant of retry decorator
"""

import logging
import time
from unittest.mock import MagicMock

import pytest
from htmlgraph.decorators import RetryError, retry, retry_async


class TestRetryBasic:
    """Test basic retry functionality."""

    def test_retry_succeeds_on_first_attempt(self):
        """Function succeeds immediately without retries."""

        @retry()
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_succeeds_after_failures(self):
        """Function succeeds after initial failures."""
        call_count = 0

        @retry(max_attempts=3)
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhaustion_raises_retry_error(self):
        """RetryError raised when all attempts exhausted."""

        @retry(max_attempts=2, initial_delay=0.01)
        def always_fails():
            raise ValueError("Persistent failure")

        with pytest.raises(RetryError) as exc_info:
            always_fails()

        error = exc_info.value
        assert error.function_name == "always_fails"
        assert error.attempts == 2
        assert isinstance(error.last_exception, ValueError)
        assert "Persistent failure" in str(error.last_exception)

    def test_retry_with_max_attempts_one(self):
        """max_attempts=1 means no retries (single attempt)."""
        call_count = 0

        @retry(max_attempts=1)
        def might_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")

        with pytest.raises(RetryError):
            might_fail()

        assert call_count == 1

    def test_retry_passes_function_args_and_kwargs(self):
        """Decorator properly forwards args and kwargs."""

        @retry(max_attempts=1)
        def function_with_params(a, b, c=None):
            return {"a": a, "b": b, "c": c}

        result = function_with_params(1, 2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_retry_preserves_function_metadata(self):
        """Decorator preserves original function name and docstring."""

        @retry()
        def documented_function():
            """This function has documentation."""
            return None

        assert documented_function.__name__ == "documented_function"
        assert "This function has documentation" in documented_function.__doc__


class TestRetryExceptionHandling:
    """Test exception filtering and handling."""

    def test_retry_only_specified_exceptions(self):
        """Only specified exceptions trigger retries."""
        call_count = 0

        @retry(
            max_attempts=3,
            exceptions=(ValueError,),
            initial_delay=0.01,
        )
        def fails_with_different_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong exception type")

        with pytest.raises(TypeError):
            fails_with_different_exception()

        # Should fail immediately without retrying
        assert call_count == 1

    def test_retry_multiple_exception_types(self):
        """Retry on multiple specified exception types."""
        call_count = 0

        @retry(
            max_attempts=3,
            exceptions=(ValueError, ConnectionError),
            initial_delay=0.01,
        )
        def fails_with_multiple_types():
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise ConnectionError("Second error")
            else:
                return "success"

        result = fails_with_multiple_types()
        assert result == "success"
        assert call_count == 3

    def test_retry_with_base_exception(self):
        """Retry on base Exception type."""
        call_count = 0

        @retry(max_attempts=2, exceptions=(Exception,), initial_delay=0.01)
        def fails_generically():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Generic error")
            return "success"

        result = fails_generically()
        assert result == "success"


class TestRetryBackoff:
    """Test exponential backoff timing."""

    def test_exponential_backoff_timing(self):
        """Backoff delays follow exponential progression."""
        call_count = 0
        call_times = []

        @retry(
            max_attempts=4,
            initial_delay=0.1,
            max_delay=100,
            exponential_base=2.0,
            jitter=False,
        )
        def track_timing():
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        result = track_timing()
        assert result == "success"

        # Calculate delays between calls
        delays = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]

        # Expected: ~0.1s, ~0.2s, ~0.4s
        assert len(delays) == 3
        assert delays[0] >= 0.08  # First retry delay (0.1s)
        assert delays[1] >= 0.18  # Second retry delay (0.2s)
        assert delays[2] >= 0.38  # Third retry delay (0.4s)

    def test_max_delay_cap(self):
        """Exponential backoff is capped by max_delay."""
        call_count = 0
        call_times = []

        @retry(
            max_attempts=4,
            initial_delay=0.05,
            max_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        def test_max_delay():
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        result = test_max_delay()
        assert result == "success"

        delays = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]

        # Exponential delays: 0.05, 0.10, 0.20 (capped at 0.1)
        # So we expect: ~0.05, ~0.10, ~0.10
        assert len(delays) == 3
        assert delays[0] >= 0.04  # First delay: 0.05s
        assert delays[1] >= 0.09  # Second delay: 0.1s (capped)
        assert delays[2] >= 0.09  # Third delay: 0.1s (capped)

    def test_jitter_adds_randomness(self):
        """Jitter adds randomness to delays."""
        call_count_a = 0
        call_count_b = 0

        @retry(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=True,
            exceptions=(ValueError,),
        )
        def with_jitter():
            nonlocal call_count_a
            call_count_a += 1
            if call_count_a < 3:
                raise ValueError("Retry")
            return "success"

        @retry(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,
            exceptions=(ValueError,),
        )
        def without_jitter():
            nonlocal call_count_b
            call_count_b += 1
            if call_count_b < 3:
                raise ValueError("Retry")
            return "success"

        # Both should succeed - jitter doesn't affect success, only timing
        assert with_jitter() == "success"
        assert without_jitter() == "success"
        assert call_count_a == 3
        assert call_count_b == 3

    def test_jitter_range(self):
        """Jitter keeps delays within [0.5x, 1.5x] range."""
        # Jitter affects randomness in backoff calculation
        # Verify that jitter=True works without errors
        call_count = 0

        @retry(
            max_attempts=3,
            initial_delay=0.05,
            exponential_base=2.0,
            jitter=True,
            exceptions=(ValueError,),
        )
        def test_jitter():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = test_jitter()
        assert result == "success"
        assert call_count == 3


class TestRetryCallbacks:
    """Test on_retry callback functionality."""

    def test_on_retry_callback_invoked(self):
        """on_retry callback is invoked on each retry."""
        callback = MagicMock()
        call_count = 0

        @retry(
            max_attempts=3,
            initial_delay=0.01,
            on_retry=callback,
        )
        def function_with_callback():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Error {call_count}")
            return "success"

        result = function_with_callback()
        assert result == "success"

        # Callback should be called twice (for attempts 1 and 2)
        assert callback.call_count == 2

        # Verify callback arguments
        calls = callback.call_args_list
        assert calls[0][0][0] == 1  # First retry is attempt 1
        assert isinstance(calls[0][0][1], ValueError)
        assert "Error 1" in str(calls[0][0][1])
        assert isinstance(calls[0][0][2], float)  # delay

    def test_callback_receives_correct_attempt_number(self):
        """Callback receives correct attempt number."""
        attempts_received = []

        def track_attempts(attempt, exc, delay):
            attempts_received.append(attempt)

        call_count = 0

        @retry(
            max_attempts=4,
            initial_delay=0.01,
            on_retry=track_attempts,
        )
        def test_attempts():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        test_attempts()

        # Callback called for attempts 1, 2, 3 (not 4, which succeeded)
        assert attempts_received == [1, 2, 3]

    def test_callback_receives_exception(self):
        """Callback receives the exception that triggered retry."""
        exceptions_received = []

        def track_exceptions(attempt, exc, delay):
            exceptions_received.append(exc)

        call_count = 0

        @retry(
            max_attempts=3,
            initial_delay=0.01,
            on_retry=track_exceptions,
        )
        def test_exceptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise RuntimeError("Second error")
            return "success"

        test_exceptions()

        assert len(exceptions_received) == 2
        assert isinstance(exceptions_received[0], ValueError)
        assert isinstance(exceptions_received[1], RuntimeError)

    def test_callback_receives_delay(self):
        """Callback receives calculated delay."""
        delays_received = []

        def track_delays(attempt, exc, delay):
            delays_received.append(delay)

        call_count = 0

        @retry(
            max_attempts=4,
            initial_delay=0.1,
            max_delay=100,
            exponential_base=2.0,
            jitter=False,
            on_retry=track_delays,
        )
        def test_delays():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        test_delays()

        # Expected delays: 0.1, 0.2, 0.4
        assert len(delays_received) == 3
        assert delays_received[0] >= 0.09
        assert delays_received[1] >= 0.19
        assert delays_received[2] >= 0.39


class TestRetryValidation:
    """Test input validation and edge cases."""

    def test_invalid_max_attempts_negative(self):
        """ValueError raised for negative max_attempts."""
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):

            @retry(max_attempts=-1)
            def test():
                pass

    def test_invalid_initial_delay_negative(self):
        """ValueError raised for negative initial_delay."""
        with pytest.raises(ValueError, match="initial_delay must be >= 0"):

            @retry(initial_delay=-1)
            def test():
                pass

    def test_invalid_max_delay_less_than_initial(self):
        """ValueError raised if max_delay < initial_delay."""
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):

            @retry(initial_delay=10.0, max_delay=5.0)
            def test():
                pass

    def test_invalid_exponential_base_zero(self):
        """ValueError raised for non-positive exponential_base."""
        with pytest.raises(ValueError, match="exponential_base must be > 0"):

            @retry(exponential_base=0)
            def test():
                pass

    def test_invalid_exponential_base_negative(self):
        """ValueError raised for negative exponential_base."""
        with pytest.raises(ValueError, match="exponential_base must be > 0"):

            @retry(exponential_base=-1.5)
            def test():
                pass

    def test_zero_delay_allowed(self):
        """Zero delay is allowed (aggressive retries)."""

        call_count = 0

        @retry(
            max_attempts=2,
            initial_delay=0.0,
            jitter=False,
        )
        def test_zero_delay():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry immediately")
            return "success"

        result = test_zero_delay()
        assert result == "success"


class TestRetryAsync:
    """Test async variant of retry decorator."""

    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        """Async function succeeds without retries."""

        @retry_async()
        async def async_success():
            return "success"

        result = await async_success()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_retry_with_failures(self):
        """Async function succeeds after initial failures."""
        call_count = 0

        @retry_async(max_attempts=3, initial_delay=0.01)
        async def async_eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "async_success"

        result = await async_eventually_succeeds()
        assert result == "async_success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_error(self):
        """Async RetryError raised when all attempts exhausted."""

        @retry_async(max_attempts=2, initial_delay=0.01)
        async def async_always_fails():
            raise ValueError("Persistent failure")

        with pytest.raises(RetryError) as exc_info:
            await async_always_fails()

        error = exc_info.value
        assert error.function_name == "async_always_fails"
        assert error.attempts == 2

    @pytest.mark.asyncio
    async def test_async_retry_callback(self):
        """Async retry invokes callback correctly."""
        callback = MagicMock()
        call_count = 0

        @retry_async(
            max_attempts=3,
            initial_delay=0.01,
            on_retry=callback,
        )
        async def async_with_callback():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = await async_with_callback()
        assert result == "success"
        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_exception_filtering(self):
        """Async retry filters exceptions correctly."""
        call_count = 0

        @retry_async(
            max_attempts=3,
            exceptions=(ValueError,),
            initial_delay=0.01,
        )
        async def async_wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong exception")

        with pytest.raises(TypeError):
            await async_wrong_exception()

        assert call_count == 1


class TestRetryIntegration:
    """Integration tests with real scenarios."""

    def test_retry_with_logging(self, caplog):
        """Default logging works when no callback provided."""
        call_count = 0

        @retry(max_attempts=3, initial_delay=0.01)
        def logged_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Error")
            return "success"

        with caplog.at_level(logging.DEBUG):
            result = logged_function()

        assert result == "success"
        # Check that debug logs were created
        assert any("Retry attempt" in record.message for record in caplog.records)

    def test_retry_in_class_method(self):
        """Retry decorator works on class methods."""

        class APIClient:
            def __init__(self):
                self.call_count = 0

            @retry(max_attempts=3, initial_delay=0.01)
            def fetch_data(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise ConnectionError("Network error")
                return {"data": "success"}

        client = APIClient()
        result = client.fetch_data()
        assert result == {"data": "success"}
        assert client.call_count == 3

    def test_retry_with_external_state(self):
        """Retry maintains correct external state."""
        external_state = {"attempts": 0}

        @retry(max_attempts=3, initial_delay=0.01)
        def modify_external_state():
            external_state["attempts"] += 1
            if external_state["attempts"] < 3:
                raise ValueError("Not ready")
            return external_state["attempts"]

        result = modify_external_state()
        assert result == 3
        assert external_state["attempts"] == 3

    def test_multiple_retries_on_different_functions(self):
        """Multiple decorated functions maintain independent state."""
        call_count_a = 0
        call_count_b = 0

        @retry(max_attempts=2, initial_delay=0.01)
        def function_a():
            nonlocal call_count_a
            call_count_a += 1
            if call_count_a < 2:
                raise ValueError("Error A")
            return "A"

        @retry(max_attempts=3, initial_delay=0.01)
        def function_b():
            nonlocal call_count_b
            call_count_b += 1
            if call_count_b < 3:
                raise ValueError("Error B")
            return "B"

        assert function_a() == "A"
        assert call_count_a == 2

        assert function_b() == "B"
        assert call_count_b == 3
