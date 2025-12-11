from typing import List

from Design_Drafter.exceptions import RetryExceededError

class RetryPolicy:
    """Manages retry logic for operations.

    Args:
        max_retries (int): Maximum number of retries.
        backoff_seconds (float): Seconds to wait between retries.

    Attributes:
        errors (List[Exception]): List of recorded errors.
        attempts (int): Number of attempts made.
    """

    def __init__(self, max_retries: int = 3, backoff_seconds: float = 0.0) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.errors: List[Exception] = []
        self.attempts: int = 0

    def record_error(self, error: Exception) -> None:
        """Record an error and increment attempt count.

        Args:
            error (Exception): The error to record.
        """
        self.errors.append(error)
        self.attempts += 1

    def should_retry(self) -> bool:
        """Determine if another retry should be attempted.

        Returns:
            bool: True if retry is allowed, False otherwise.
        """
        return self.attempts < self.max_retries

    def error_context(self) -> str:
        """Get a summary of all recorded errors.

        Returns:
            str: Error context string.
        """
        return "; ".join(f"{type(e).__name__}: {e}" for e in self.errors)

    def reset(self) -> None:
        """Reset the retry state."""
        self.errors.clear()
        self.attempts = 0

    def error_context_list(self):
        """Get a list of (attempt, str(error)) tuples for all recorded errors."""
        return [(i + 1, str(e)) for i, e in enumerate(self.errors)]