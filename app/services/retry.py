"""Bounded exponential-backoff retries for transient external calls."""

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_call(operation: Callable[[], T], attempts: int = 3, base_delay: float = 0.5) -> T:
    attempts = max(1, min(attempts, 5))
    for attempt in range(attempts):
        try:
            return operation()
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(min(base_delay * (2**attempt), 8.0) * random.uniform(0.5, 1.5))
    raise RuntimeError("Retry operation did not return.")
