import pytest


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleep_calls = []

    def monotonic(self):
        return self.now

    async def sleep(self, dt: float):
        self.sleep_calls.append(dt)
        self.now += max(0.0, float(dt))

    def now_approx_equals(self, expected: float, tolerance: float = 0.001):
        return abs(self.now - expected) <= tolerance


@pytest.fixture
def fake_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr("time.monotonic", clock.monotonic)
    monkeypatch.setattr("asyncio.sleep", clock.sleep)
    return clock
