from lazy_limiter import TokenBucketRateLimiter
import pytest
from pytest import approx
import asyncio


class Clock:
    def __init__(self):
        self._time = 0.0

    def advance(self, seconds: float):
        self._time += seconds

    def __call__(self):
        return self._time


async def test_token_bucket_rate_limiter():
    # Create a TokenBucketRateLimiter with a capacity of 10 tokens and a refill rate of 1 token per second
    clock = Clock()

    limiter = TokenBucketRateLimiter(capacity=10, refill_per_second=1, clock=clock)

    # Check initial available tokens
    assert limiter.available == 10

    # Consume 5 tokens
    limiter.consume(5)
    assert limiter.available == 5

    # Time to available for 3 tokens should be 0 since we have 5 available still
    assert limiter.time_to_available(3) == 0

    # Wait for 2 seconds and check available tokens
    clock.advance(2)
    assert limiter.available == approx(7)

    # Consume all remaining tokens
    limiter.consume(7)
    assert limiter.available == 0

    # Time to available for 10 tokens should be 10 seconds
    assert limiter.time_to_available(10) == 10.0

    # Wait for 10 seconds and check available tokens
    clock.advance(5)
    assert limiter.available == 5
    assert limiter.time_to_available(10) == 5.0
    clock.advance(5)
    assert limiter.available == 10
