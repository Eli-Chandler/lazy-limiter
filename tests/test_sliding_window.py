from lazy_limiter import SlidingWindowRateLimiter
from pytest import approx


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

    limiter = SlidingWindowRateLimiter(requests_per_window=10, window_seconds=1, clock=clock)

    # Check initial available tokens
    assert limiter.available == 10
    assert limiter.time_to_available(10) == 0

    limiter.consume(1)
    assert limiter.available == 9
    assert limiter.time_to_available(10) == approx(1)

    clock.advance(0.9)
    assert limiter.available == 9
    assert limiter.time_to_available(10) == approx(0.1)

    clock.advance(0.1)
    assert limiter.available == 10

    for _ in range(10):
        limiter.consume(1)
        clock.advance(0.1)

    assert limiter.available == 1
    assert limiter.time_to_available(0) == 0
    assert limiter.time_to_available(1) == 0
    assert limiter.time_to_available(2) == approx(0.1)
    assert limiter.time_to_available(3) == approx(0.2)
    for requests in range(3, 11):
        assert limiter.time_to_available(requests) == approx((requests - 1) * 0.1)

    clock.advance(1)
    assert limiter.available == 10

    limiter.consume(2)
    assert limiter.available == 8
    assert limiter.time_to_available(9) == approx(1)
    assert limiter.time_to_available(10) == approx(1)