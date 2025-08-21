import time
from typing import Callable

from lazy_limiter.base import RateLimiter


class TokenBucketRateLimiter(RateLimiter):
    def __init__(
        self,
        capacity: int | float,
        refill_per_second: int | float,
        starting_tokens: int | float = None,
        clock: Callable[[], float] = None,
    ):
        super().__init__()
        self._token_capacity = float(capacity)
        self._tokens_per_second = float(refill_per_second)
        self._tokens = float(
            starting_tokens if starting_tokens is not None else capacity
        )
        self._last_refill = clock() if clock else 0.0
        self._clock = clock if clock is not None else lambda: time.monotonic()

    @property
    def available(self) -> int | float:
        now = self._clock()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(
            self._token_capacity, self._tokens + elapsed * self._tokens_per_second
        )
        return self._tokens

    @property
    def capacity(self) -> int | float:
        return self._token_capacity

    def consume(self, requests: int | float = 1) -> None:
        self._tokens -= requests

    def time_to_available(self, requests: int | float = 1) -> float:
        available = self.available
        if requests <= available:
            return 0.0
        needed = requests - available
        return needed / self._tokens_per_second
