import asyncio
from collections import defaultdict
from typing import Callable

from lazy_limiter.base import RateLimiter, RateLimiterProtocol


class KeyedRateLimiter:
    def __init__(
        self,
        rate_limit_limiter_factory: Callable[[str], RateLimiter | RateLimiterProtocol],
        grace_period_seconds: int | float = 1,
    ):
        self._rate_limit_limiter_factory = rate_limit_limiter_factory
        self._grace_period_seconds = grace_period_seconds
        self._cleaner_tasks: dict[str, asyncio.Task] = {}
        self._rate_limiters: dict[str, RateLimiterProtocol] = {}

    async def acquire(self, key: str, requests: int | float = 1) -> None:
        rate_limiter = await self.get_rate_limiter(key)
        await rate_limiter.acquire(requests)

    async def acquire_nowait(self, key: str, requests: int | float = 1) -> bool:
        rate_limiter = await self.get_rate_limiter(key)
        acquired = rate_limiter.acquire_nowait(requests)
        return acquired

    async def get_rate_limiter(self, key: str) -> RateLimiterProtocol:
        if key not in self._rate_limiters:
            rate_limiter = self._rate_limit_limiter_factory(key)
            self._rate_limiters[key] = rate_limiter
            self._cleaner_tasks[key] = asyncio.create_task(
                self._cleaner(key, rate_limiter)
            )
            return rate_limiter

        return self._rate_limiters[key]

    async def _cleaner(self, key: str, rate_limiter: RateLimiterProtocol) -> None:
        while True:
            await asyncio.sleep(
                rate_limiter.time_to_unused() + self._grace_period_seconds
            )

            if rate_limiter.is_unused:
                del self._rate_limiters[key]
                del self._cleaner_tasks[key]
                return
