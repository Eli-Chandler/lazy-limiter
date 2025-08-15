import asyncio
from collections import defaultdict
from typing import Optional

from lazy_limiter.token_bucket import TokenBucket


class KeyedTokenBucket:
    _token_buckets: dict[str, TokenBucket]
    _kill_bucket_tasks: dict[str, asyncio.Task]

    def __init__(
        self,
        token_capacity: int | float,
        tokens_per_second: int | float,
        starting_tokens: Optional[int | float] = None,
    ):
        self._token_buckets = defaultdict(
            lambda: TokenBucket(
                token_capacity, tokens_per_second, starting_tokens=starting_tokens
            )
        )
        self._kill_bucket_tasks = {}

    async def acquire(self, key: str):
        bucket = self._token_buckets[key]
        await bucket.acquire()

        async def _kill_bucket_if_full():
            await asyncio.sleep(bucket.time_to_capacity(bucket.tokens))
            if bucket.is_full:
                del self._token_buckets[key]
            del self._kill_bucket_tasks[key]

        existing_task = self._kill_bucket_tasks.get(key)
        if existing_task is not None:
            existing_task.cancel()
        task = asyncio.create_task(_kill_bucket_if_full())
        self._kill_bucket_tasks[key] = task
