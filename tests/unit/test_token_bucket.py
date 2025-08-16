import asyncio

import pytest
from pytest import approx

from lazy_limiter import TokenBucket


async def test_acquire_waits_for_refill_total_elapsed(clock, assert_takes_time):
    tb = TokenBucket(capacity=5, refill_per_second=5, starting_tokens=0, clock=clock)

    with assert_takes_time(1.0):
        with assert_takes_time(0.6):
            await tb.acquire(3)
        with assert_takes_time(0.4):
            await tb.acquire(2)

    await asyncio.sleep(1)

    with assert_takes_time(0):
        await tb.acquire(5)

async def test_parallel_acquire(clock, assert_takes_time):
    tb = TokenBucket(capacity=10, refill_per_second=10, starting_tokens=0, clock=clock)

    async def how_long_to_acquire(tokens):
        start = clock()
        await tb.acquire(tokens)
        return clock() - start

    task_1 = asyncio.create_task(how_long_to_acquire(5))
    task_2 = asyncio.create_task(how_long_to_acquire(5))

    with assert_takes_time(1.0):
        result_1 = await task_1
        result_2 = await task_2

    assert approx(0.5) in (result_1, result_2)
    assert approx(1.0) in (result_1, result_2)

async def test_take_all_tokens(clock, assert_takes_time):
    tb = TokenBucket(capacity=10, refill_per_second=10, starting_tokens=0, clock=clock)
    with assert_takes_time(1.0):
        await tb.acquire(10)
    assert tb.tokens == approx(0)

async def test_take_more_than_capacity(clock, assert_takes_time):
    tb = TokenBucket(capacity=10, refill_per_second=10, starting_tokens=0, clock=clock)

    with pytest.raises(ValueError):
        tb.acquire_nowait(11)

    with pytest.raises(ValueError):
        await tb.acquire(11)


def test_full_behaviour():
    tb = TokenBucket(capacity=10, refill_per_second=10, starting_tokens=0)

    assert tb.is_full is False
    tb._tokens = 10
    assert tb.is_full is True

    tb._tokens = 5
    assert tb.is_full is False

    tb._tokens = 0
    assert tb.is_full is False

    tb._tokens = 10.1
    assert tb.is_full is True

    tb._tokens = 10
    assert tb.is_full is True

    tb._waiters = 1
    assert tb.is_full is False