import asyncio
from abc import ABC, abstractmethod
from typing import Protocol


class RateLimiterProtocol(Protocol):
    def acquire_nowait(self, requests: int | float = 1) -> bool:
        """Check if the rate limiter can immediately accommodate the requested number of requests."""
        ...

    async def acquire(self, requests: int | float = 1) -> None:
        """Acquire the requested number of requests, waiting if necessary."""
        ...

    def time_to_unused(self) -> float:
        """Return the time until the rate limiter is unused (i.e. available == capacity and no pending acquire calls)."""
        ...

    @property
    def is_unused(self) -> bool:
        """If the rate limiter is unused, meaning available >= capacity and no pending acquire calls."""
        ...


class RateLimiter(ABC, RateLimiterProtocol):
    def __init__(self):
        self._waiters = 0

    @property
    @abstractmethod
    def available(self) -> int | float:
        """Return the number of requests currently available in the rate limiter."""
        pass

    @property
    @abstractmethod
    def capacity(self) -> int | float:
        """Return the maximum number of requests that can be accommodated by the rate limiter."""
        pass

    @abstractmethod
    def consume(self, requests: int | float = 1) -> None:
        """Consume the specified number of requests from the rate limiter."""
        pass

    @abstractmethod
    def time_to_available(self, requests: int | float = 1) -> float:
        """Return the time until available >= requests, assuming no additional requests are made."""
        pass

    def _time_to_available(self, requests: int | float = 1) -> float:
        if requests > self.capacity:
            raise ValueError(
                f"Requests requested ({requests}) exceed rate limiter capacity ({self.capacity})"
            )
        return self.time_to_available(requests)

    def acquire_nowait(self, requests: int | float = 1) -> bool:
        if requests < 0:
            raise ValueError("Requests must be a non-negative number")
        if requests > self.capacity:
            raise ValueError(
                f"Requests requested ({requests}) exceed rate limiter capacity ({self.capacity})"
            )
        if requests > self.available:
            return False

        self.consume(requests)
        return True

    async def acquire(self, requests: int | float = 1) -> None:
        try:
            self._waiters += 1
            while True:
                if self.acquire_nowait(requests):
                    return
                await asyncio.sleep(self._time_to_available(requests))
        finally:
            self._waiters -= 1

    def time_to_unused(self):
        if self.available >= self.capacity:
            return 0.0

        return max(self._time_to_available(self.capacity), 0.0)

    @property
    def is_unused(self) -> bool:
        return self.available >= self.capacity and self._waiters == 0
