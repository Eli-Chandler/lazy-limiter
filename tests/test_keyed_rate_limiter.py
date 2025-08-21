import asyncio

from lazy_limiter import TokenBucketRateLimiter, KeyedRateLimiter
from .utils import assert_takes_time


async def test_keyed_rate_limiter():
    rate_limiter_factory = lambda key: TokenBucketRateLimiter(
        capacity=10, refill_per_second=10, starting_tokens=10
    )

    keyed_limiter = KeyedRateLimiter(
        rate_limit_limiter_factory=rate_limiter_factory, grace_period_seconds=1
    )

    with assert_takes_time(0):
        await keyed_limiter.acquire("test_key", requests=5)
    with assert_takes_time(0):
        await keyed_limiter.acquire("test_key", requests=5)

    assert len(keyed_limiter._rate_limiters) == 1
    assert len(keyed_limiter._cleaner_tasks) == 1

    with assert_takes_time(0.5):
        await keyed_limiter.acquire("test_key", requests=5)
    with assert_takes_time(0):
        await keyed_limiter.acquire("test_key_2", requests=10)
    with assert_takes_time(0.5):
        await keyed_limiter.acquire("test_key_2", requests=5)

    assert len(keyed_limiter._rate_limiters) == 2
    assert len(keyed_limiter._cleaner_tasks) == 2

    await asyncio.sleep(1.1)  # After 1 second the first key should be cleaned up
    assert len(keyed_limiter._rate_limiters) == 1
    assert len(keyed_limiter._cleaner_tasks) == 1
    assert "test_key" not in keyed_limiter._rate_limiters
    assert "test_key" not in keyed_limiter._cleaner_tasks

    await asyncio.sleep(0.5)

    assert len(keyed_limiter._rate_limiters) == 0
    assert len(keyed_limiter._cleaner_tasks) == 0
