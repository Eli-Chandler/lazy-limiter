import asyncio
from contextlib import contextmanager

import pytest
import looptime


class LooptimeEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        loop = super().new_event_loop()
        return looptime.patch_event_loop(loop)

@pytest.fixture
def event_loop_policy():
    return LooptimeEventLoopPolicy()

@pytest.fixture
def clock():
    return lambda: asyncio.get_running_loop().time()

@pytest.fixture
def assert_takes_time(clock):
    @contextmanager
    def _takes_time(seconds):
        start = clock()
        yield
        elapsed = clock() - start
        assert elapsed == pytest.approx(seconds, abs=0.05), f"Expected {seconds}s, got {elapsed}s"

    return _takes_time