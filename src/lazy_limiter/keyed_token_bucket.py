import asyncio
import time
from collections import defaultdict
from typing import Optional, Callable

from lazy_limiter.token_bucket import TokenBucket
import heapq


class KeyedTokenBucket:
    _token_buckets: dict[str, TokenBucket]
    _clock: Callable[[], float]

    def __init__(
        self,
        capacity: int | float,
        refill_per_second: int | float,
        starting_tokens: Optional[int | float] = None,
        deletion_grace_period_seconds: int | float = 1.0,
        clock: Callable[[], float] = None,
    ):
        self._token_buckets = defaultdict(
            lambda: TokenBucket(
                capacity, refill_per_second, starting_tokens=starting_tokens
            )
        )
        # Deadline, key, TokenBucket
        self._heap: list[tuple[float, str, TokenBucket]] = []
        self._poke = asyncio.Event()
        self._cleaner_task = asyncio.create_task(self._cleaner())
        self.deletion_grace_period_seconds = deletion_grace_period_seconds
        self._clock = clock if clock is not None else time.monotonic

    async def acquire(self, key: str, tokens: int | float = 1) -> None:
        bucket = self._token_buckets[key]
        await bucket.acquire(tokens)

        deadline = (
            self._clock()
            + bucket.time_to_capacity(bucket.token_capacity)
            + self.deletion_grace_period_seconds
        )
        heapq.heappush(self._heap, (deadline, key, bucket))
        self._poke.set()

    async def _cleaner(self):
        while True:
            if not self._heap:
                await self._poke.wait()
                self._poke.clear()

            deadline, key, bucket = heapq.heappop(self._heap)
            now = self._clock()
            if deadline > now:
                await asyncio.sleep(deadline - now)

            # only delete if the dict still points at the same bucket and it's full
            if (
                bucket.is_full
                and key in self._token_buckets
                and self._token_buckets[key] is bucket
            ):
                del self._token_buckets[key]
