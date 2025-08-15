from lazy_limiter import TokenBucket
from .conftest import FakeClock


async def test_token_bucket_acquire(fake_clock: FakeClock):
    # Arrange
    bucket = TokenBucket(capacity=10, refill_per_second=1, starting_tokens=10)
    assert bucket.tokens == 10
    assert bucket.token_capacity == 10
    assert bucket.tokens_per_second == 1

    # Act
    await bucket.acquire(5)
    assert bucket.tokens == 5
    assert fake_clock.now_approx_equals(0.0)

    await bucket.acquire(10)
    assert bucket.tokens == 0
    assert fake_clock.now_approx_equals(5.0)


async def test_token_bucket_acquire_nowait(fake_clock: FakeClock):
    # Arrange
    bucket = TokenBucket(capacity=10, refill_per_second=1, starting_tokens=10)
    assert bucket.tokens == 10

    # Act
    assert bucket.acquire_nowait(5) is True
    assert bucket.tokens == 5

    assert bucket.acquire_nowait(6) is False
    assert bucket.tokens == 5

    # Simulate time passing to allow the bucket to refill
    fake_clock.now += 5.0

    assert bucket.acquire_nowait(6) is True
    assert bucket.tokens == 4

    assert bucket.acquire_nowait(4) is True
