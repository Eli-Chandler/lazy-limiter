import asyncio
import time
from typing import Optional


class TokenBucket:
    token_capacity: float
    tokens_per_second: float
    tokens: float
    _last_refill: float
    _waiters: int

    def __init__(
        self,
        capacity: int | float,
        refill_per_second: int | float,
        starting_tokens: Optional[int | float] = None,
    ):
        self.tokens = float(
            starting_tokens if starting_tokens is not None else capacity
        )
        self.token_capacity = float(capacity)
        self.tokens_per_second = float(refill_per_second)
        self._last_refill = time.monotonic()
        self._waiters = 0

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        if elapsed <= 0:
            return

        new_tokens = elapsed * self.tokens_per_second
        self.tokens = min(self.token_capacity, self.tokens + new_tokens)

    def time_to_capacity(self, tokens: int | float) -> float:
        if tokens > self.token_capacity:
            raise ValueError(
                f"Tokens requested ({tokens}) exceed bucket capacity ({self.token_capacity})"
            )

        if tokens - self.tokens <= 0:
            return 0.0

        return (tokens - self.tokens) / self.tokens_per_second

    async def acquire(self, tokens: int | float = 1) -> None:
        if self.acquire_nowait(tokens):
            return

        try:
            self._waiters += 1
            while True:
                if self.acquire_nowait(tokens):
                    return
                # The amount of time we need to wait for the bucket to possibly have enough tokens
                await asyncio.sleep(self.time_to_capacity(tokens))
        finally:
            self._waiters -= 1

    def acquire_nowait(self, tokens: int | float = 1) -> bool:
        if tokens <= 0:
            raise ValueError("Tokens must be a positive number")
        if tokens > self.token_capacity:
            raise ValueError(
                f"Tokens requested ({tokens}) exceed bucket capacity ({self.token_capacity})"
            )

        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def is_full(self) -> bool:
        self._refill()
        # Check if no waiters, otherwise those tokens are about to get spent so the bucket is not considered full
        return self.tokens >= self.token_capacity and self._waiters == 0
