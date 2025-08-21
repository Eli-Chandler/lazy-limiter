import asyncio
import itertools
import pytest

from lazy_limiter.base import RateLimiter
from unittest.mock import Mock

from .utils import assert_takes_time


class MockedRateLimiter(RateLimiter):
    def __init__(self):
        super().__init__()
        self.available_mock = Mock()
        self.capacity_mock = Mock()
        self.consume_mock = Mock()
        self.time_to_available_mock = Mock()

    @property
    def available(self) -> int | float:
        return self.available_mock()

    @property
    def capacity(self) -> int | float:
        return self.capacity_mock()

    def consume(self, requests: int | float = 1) -> None:
        self.consume_mock(requests)

    def time_to_available(self, requests: int | float = 1) -> float:
        return self.time_to_available_mock(requests)


@pytest.fixture
def rl():
    return MockedRateLimiter()


def test_internal_time_to_available_request_greater_than_capacity(rl):
    rl.capacity_mock.return_value = 10

    with pytest.raises(ValueError):
        rl._time_to_available(11)


def test_internal_time_to_available(rl):
    rl.capacity_mock.return_value = 10
    rl.time_to_available_mock.return_value = 5.0

    result = rl._time_to_available(5)
    assert result == 5.0

    rl.time_to_available_mock.assert_called_once_with(5)


def test_acquire_nowait_negative(rl):
    with pytest.raises(ValueError):
        rl.acquire_nowait(-1)


def test_acquire_nowait_exceed_capacity(rl):
    rl.capacity_mock.return_value = 10

    with pytest.raises(ValueError):
        rl.acquire_nowait(11)


def test_acquire_nowait_success(rl):
    rl.available_mock.return_value = 10
    rl.capacity_mock.return_value = 10

    result = rl.acquire_nowait(5)
    assert result is True

    rl.available_mock.assert_called_once()
    rl.capacity_mock.assert_called_once()
    rl.consume_mock.assert_called_once_with(5)


def test_acquire_nowait_failure(rl):
    rl.available_mock.return_value = 5
    rl.capacity_mock.return_value = 10

    result = rl.acquire_nowait(6)
    assert result is False

    rl.available_mock.assert_called_once()
    rl.capacity_mock.assert_called_once()
    rl.consume_mock.assert_not_called()


async def test_acquire_success(rl):
    rl.available_mock.return_value = 4
    rl.capacity_mock.return_value = 10
    rl.time_to_available_mock.return_value = 0.1

    assert rl._waiters == 0
    with assert_takes_time(0.1):
        task = asyncio.create_task(rl.acquire(5))
        await asyncio.sleep(0)  # Yield control to allow the task to start
        assert rl._waiters == 1
        await asyncio.sleep(0.05)  # Simulate some time passing
        rl.consume_mock.assert_not_called()
        rl.available_mock.return_value = 5
        await task

    assert rl._waiters == 0
    rl.consume_mock.assert_called_once_with(5)


async def test_concurrent_acquire(rl):
    rl.available_mock.side_effect = itertools.chain([6, 3, 0, 0, 3, 0, 3])
    rl.capacity_mock.return_value = 10
    rl.time_to_available_mock.return_value = 0.1

    async def acquire_task(requests):
        await rl.acquire(requests)

    tasks = [asyncio.create_task(acquire_task(3)) for _ in range(4)]

    # Ensure 1 task finishes immediately
    with assert_takes_time(0):
        done = []
        while len(done) < 2:
            new_done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            done.extend(new_done)
    assert len(done) == 2

    tasks = pending

    with assert_takes_time(0.1):
        # Ensure the next task waits for available tokens
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    assert len(done) == 1

    with assert_takes_time(0.1):
        # Ensure the next task waits for available tokens
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
    assert len(done) == 1
    assert len(pending) == 0  # Make sure I'm not stupid


async def test_acquire_negative(rl):
    with pytest.raises(ValueError):
        await rl.acquire(-1)


async def test_acquire_exceed_capacity(rl):
    rl.capacity_mock.return_value = 10

    with pytest.raises(ValueError):
        await rl.acquire(11)


async def test_time_to_unused(rl):
    rl.available_mock.return_value = 1
    rl.time_to_available_mock.return_value = 5
    rl.capacity_mock.return_value = 10
    assert rl.time_to_unused() == 5

    rl.time_to_available_mock.assert_called_once_with(10)


async def test_is_unused_not_at_capacity(rl):
    rl.available_mock.return_value = 5
    rl.capacity_mock.return_value = 10
    assert not rl.is_unused


async def test_is_unused_not_at_capacity_with_waiters(rl):
    rl.available_mock.return_value = 5
    rl.capacity_mock.return_value = 10
    rl._waiters = 1
    assert not rl.is_unused


async def test_is_unused_at_capacity_with_waiters(rl):
    rl.available_mock.return_value = 10
    rl.capacity_mock.return_value = 10
    rl._waiters = 1
    assert not rl.is_unused


async def test_is_unused_at_capacity(rl):
    rl.available_mock.return_value = 10
    rl.capacity_mock.return_value = 10
    assert rl.is_unused
