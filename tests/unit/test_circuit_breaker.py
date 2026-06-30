"""Unit tests: circuit breaker state machine (deterministic via injected clock)."""

import asyncio

from autosre_shared.resilience.circuit_breaker import (
    CircuitBreaker,
    BreakerState,
    CircuitBreakerOpenError,
)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, d):
        self.t += d


def test_opens_after_threshold():
    b = CircuitBreaker("u1", failure_threshold=3, recovery_timeout=10, clock=Clock())
    assert b.state == BreakerState.CLOSED
    for _ in range(3):
        assert b.allow() is True
        b.record_failure()
    assert b.state == BreakerState.OPEN
    assert b.allow() is False


def test_half_open_then_close():
    clk = Clock()
    b = CircuitBreaker(
        "u2", failure_threshold=2, recovery_timeout=10, success_threshold=2, clock=clk
    )
    b.record_failure()
    b.record_failure()
    assert b.state == BreakerState.OPEN
    clk.advance(10)
    assert b.allow() is True
    assert b.state == BreakerState.HALF_OPEN
    b.record_success()
    assert b.state == BreakerState.HALF_OPEN
    b.record_success()
    assert b.state == BreakerState.CLOSED


def test_failed_trial_reopens():
    clk = Clock()
    b = CircuitBreaker("u3", failure_threshold=1, recovery_timeout=5, clock=clk)
    b.record_failure()
    assert b.state == BreakerState.OPEN
    clk.advance(5)
    b.allow()
    assert b.state == BreakerState.HALF_OPEN
    b.record_failure()
    assert b.state == BreakerState.OPEN


def test_protect_rejects_when_open():
    b = CircuitBreaker("u4", failure_threshold=1, clock=Clock())
    b.record_failure()

    async def go():
        try:
            async with b.protect():
                pass
            return False
        except CircuitBreakerOpenError:
            return True

    assert asyncio.run(go()) is True


def test_call_records_outcomes():
    b = CircuitBreaker("u5", failure_threshold=2, clock=Clock())

    async def ok():
        return 42

    async def boom():
        raise ValueError("x")

    assert asyncio.run(b.call(ok)) == 42
    for _ in range(2):
        try:
            asyncio.run(b.call(boom))
        except ValueError:
            pass
    assert b.state == BreakerState.OPEN


def test_snapshot_shape():
    b = CircuitBreaker("u6", clock=Clock())
    snap = b.snapshot()
    assert snap["name"] == "u6"
    assert snap["state"] == "closed"
    assert snap["config"]["failure_threshold"] == 5
