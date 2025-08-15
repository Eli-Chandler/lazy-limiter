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

## Usage

```python
from lazy_limiter import TokenBucket, KeyedTokenBucket
```

```python
bucket = TokenBucket(capacity=5, refill_per_second=1)
await bucket.acquire()
```

```python
bucket = KeyedTokenBucket(capacity=1, refill_per_second=0.5)
# No blocking here, hello and world each have their own bucket
await keyed.acquire("hello")
await keyed.acquire("world")

# 0.5 second delay here because "world" bucket would be empty
await keyed.acquire("world")
# hello and world bucket are now full, and have no waiters, so they will be removed
```
