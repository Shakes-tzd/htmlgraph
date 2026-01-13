def factorial(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer.

    Args:
        n: A non-negative integer for which to calculate the factorial.

    Returns:
        The factorial of n (n!).

    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.

    Examples:
        >>> factorial(0)
        1
        >>> factorial(5)
        120
        >>> factorial(10)
        3628800
    """
    if not isinstance(n, int):
        raise TypeError(f"Expected int, got {type(n).__name__}")

    if n < 0:
        raise ValueError(f"Factorial not defined for negative numbers: {n}")

    if n == 0 or n == 1:
        return 1

    result = 1
    for i in range(2, n + 1):
        result *= i

    return result
