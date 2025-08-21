import asyncio
from contextlib import contextmanager

import pytest


@contextmanager
def assert_takes_time(seconds: float):
    start = asyncio.get_event_loop().time()
    yield
    end = asyncio.get_event_loop().time()
    elapsed = end - start
    assert elapsed == pytest.approx(seconds, abs=0.02)
