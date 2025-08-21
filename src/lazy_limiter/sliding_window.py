import time
from collections import deque
from typing import Callable

from lazy_limiter.base import RateLimiter


class SlidingWindowRateLimiter(RateLimiter):
    def __init__(
        self,
        requests_per_window: float | int,
        window_seconds: float | int,
        clock: Callable[[], float] | None = None,
    ):
        super().__init__()
        self._requests_per_window = requests_per_window
        self._window_seconds = window_seconds
        # deque[requests, eviction_time]
        self._requests: deque[tuple[float, float]] = deque()
        self._clock = clock if clock is not None else time.monotonic

    @property
    def available(self) -> int | float:
        now = self._clock()
        while self._requests and self._requests[0][1] <= now:
            self._requests.popleft()
        return self._requests_per_window - sum(t[0] for t in self._requests)

    @property
    def capacity(self) -> int | float:
        return self._requests_per_window

    def consume(self, requests: int | float = 1) -> None:
        self._requests.append((requests, self._clock() + self._window_seconds))

    def time_to_available(self, requests: int | float = 1) -> float:
        currently_available = self.available

        if currently_available >= requests:
            return 0.0

        now = self._clock()

        for req, eviction_time in self._requests:
            currently_available += req
            if currently_available >= requests:
                return eviction_time - now

        raise RuntimeError(
            "Couldn't get enough tokens even after fully evicting everything. Base class should guard against this. This should not happen."
        )
