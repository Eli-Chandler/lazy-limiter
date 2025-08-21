from lazy_limiter import KeyedRateLimiter

# lazy_limiter

A minimal async friendly token bucket and keyed token bucket for Python.

It is called "lazy" for two reasons:

1. I am lazy. I got tired of rewriting token buckets every time I needed one.
2. The buckets are lazy. They are created only when needed and automatically removed when full and idle.

## Features

- TokenBucket: simple token bucket
- KeyedTokenBucket: one bucket per key, created on demand, auto cleaned when idle
- Async friendly
- No dependencies
- Small and easy to read

## Note
- Async safe, not thread safe.

## Installation

```bash
pip install git+<this_repo_url>
```

If you want this as a PyPI package, please open an issue or PR.


## Note:
* All limiters are **async-safe** (await/`asyncio`), but **not necessarily thread-safe** (may change at some point).
* If you implement your own limiter, make sure your `available` and `time_to_available` are inexpensive and updates internal state as needed (see `TokenBucketRateLimiter` for a lightweight pattern).

# Examples

## 1) Keyed rate limiting (one bucket per key)

Create a `KeyedRateLimiter` that builds a per-key token bucket on demand. Keys can be user IDs, API keys, chat IDs—anything hashable.

```python
import asyncio
from lazy_limiter import KeyedRateLimiter, TokenBucketRateLimiter

keyed = KeyedRateLimiter(rate_limit_limiter_factory=lambda _key: TokenBucketRateLimiter(capacity=10, refill_per_second=1))

async def work(user_id: str, n: int):
    for i in range(n):
        await keyed.acquire(user_id)  # waits if the user's bucket is empty
        print(f"[{user_id}] allowed request {i}")

async def main():
    await asyncio.gather(
        work("alice", 6),
        work("alice", 6), # This will get blocked for 1 second
        work("bob", 6), # This will not get blocked
    )

asyncio.run(main())
```

### Non-blocking acquire

```python
ok = await keyed.acquire_nowait("alice")
if not ok:
    # fall back to queue, shed load, or return HTTP 429
    ...
```

---

## 2) Per-key policies (use the key inside the factory)

Use the key to decide the bucket’s size and refill rate dynamically.

```python
from lazy_limiter import KeyedRateLimiter, TokenBucketRateLimiter
from lazy_limiter.base import RateLimiterProtocol

def factory(key: str) -> RateLimiterProtocol:
    if key.startswith("free"):
        return TokenBucketRateLimiter(capacity=5, refill_per_second=1)  # free tier
    elif key.startswith("pro"):
        return TokenBucketRateLimiter(capacity=20, refill_per_second=5)  # elite tier
    else:
        raise ValueError(f"Unknown key prefix: {key}")

keyed_by_plan = KeyedRateLimiter(rate_limit_limiter_factory=factory)

# Usage:
# await keyed_by_plan.acquire("pro_123")  # "p" pro rate limits
# await keyed_by_plan.acquire("free_123") # "free" rate limits
```

The keyed limiter will lazily create the right bucket when each API key is first seen and automatically garbage-collect it after it’s full and idle.

---

## 3) Plain token bucket (no keys)

If you just need a single global limiter, use `TokenBucketRateLimiter` directly.

```python
import asyncio
from lazy_limiter import TokenBucketRateLimiter

# Allow bursts up to 10, refill at 3 tokens per second
bucket = TokenBucketRateLimiter(capacity=10, refill_per_second=3)

async def call_backend(i: int):
    await bucket.acquire()  # blocks until a token is available
    print(f"sent request {i}")

async def main():
    await asyncio.gather(*(call_backend(i) for i in range(25)))

asyncio.run(main())
```

### Try `acquire_nowait` for fast-fail

```python
if not bucket.acquire_nowait():
    # don't block — respond with 429 or enqueue
    ...
```

---

## 4) Roll your own limiter in \~30 lines (using the ABC)

Implementing a custom limiter is intentionally simple. Here’s a **fixed-window** rate limiter that allows up to `capacity` requests per window (in seconds). This demonstrates the minimal methods you need to provide.

```python
import time
import asyncio
from lazy_limiter.base import RateLimiter

class FixedWindowRateLimiter(RateLimiter):
    """
    Allow up to `capacity` requests every `window_seconds`.
    Resets counters at the window boundary.
    """
    def __init__(self, capacity: int, window_seconds: float, clock=None):
        super().__init__()
        self._capacity = float(capacity)
        self._window_seconds = float(window_seconds)
        self._clock = clock or time.monotonic
        self._window_start = self._clock()
        self._used = 0.0

    @property
    def capacity(self) -> float:
        return self._capacity

    @property
    def available(self) -> float:
        now = self._clock()
        if now - self._window_start >= self._window_seconds:
            # start a new window
            self._window_start = now
            self._used = 0.0
        return max(self._capacity - self._used, 0.0)

    def consume(self, requests: float = 1) -> None:
        self._used += requests

    def time_to_available(self, requests: float = 1) -> float:
        # If we can serve now, no wait; else wait until next window
        if requests <= self.available:
            return 0.0
        now = self._clock()
        elapsed = now - self._window_start
        return self._window_seconds - elapsed

# Usage example
async def main():
    limiter = FixedWindowRateLimiter(capacity=5, window_seconds=1.0)
    for i in range(12):
        await limiter.acquire()
        print(f"allowed {i}")

asyncio.run(main())
```

You can drop this custom limiter into `KeyedRateLimiter` by returning it from the factory:

Note: In addition to `RateLimiter`, which is an ABC with some concrete methods there is also `RateLimiterProtocol` if you want to implement from scratch.

```python
from lazy_limiter import KeyedRateLimiter

def fixed_window_factory(_key: str) -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(capacity=5, window_seconds=1.0)

keyed_fixed = KeyedRateLimiter(rate_limit_limiter_factory=fixed_window_factory)
# await keyed_fixed.acquire("user-123")
```

The `capacity` and `time_to_available` methods will be used to automatically purge idle buckets.

---

## 5) Mixing & matching (hybrid strategies)

Because `KeyedRateLimiter` accepts any `RateLimiterProtocol`, you can route different keys to different limiter types:

```python
from lazy_limiter import KeyedRateLimiter, TokenBucketRateLimiter

def hybrid_factory(key: str):
    if key.startswith("burst-"):
        return TokenBucketRateLimiter(capacity=50, refill_per_second=10)  # bursty
    else:
        return FixedWindowRateLimiter(capacity=10, window_seconds=1.0)    # steady

hybrid = KeyedRateLimiter(rate_limit_limiter_factory=hybrid_factory)

# await hybrid.acquire("burst-42")  # token bucket
# await hybrid.acquire("user-17")   # fixed window
```
