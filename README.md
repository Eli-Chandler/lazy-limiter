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