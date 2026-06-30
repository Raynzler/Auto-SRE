"""Unit tests: token bucket algorithm + 429 middleware behaviour."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autosre_shared.resilience.rate_limiter import (
    RateLimiter,
    InMemoryBucketStore,
    RateLimitMiddleware,
)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, d):
        self.t += d


def test_burst_then_reject():
    clk = Clock()
    rl = RateLimiter(rps=1, burst=3, store=InMemoryBucketStore(1, 3, clk))
    results = [rl.check("client").allowed for _ in range(4)]
    assert results == [True, True, True, False]


def test_retry_after_positive_when_rejected():
    clk = Clock()
    rl = RateLimiter(rps=2, burst=1, store=InMemoryBucketStore(2, 1, clk))
    assert rl.check("c").allowed is True
    rejected = rl.check("c")
    assert rejected.allowed is False
    assert rejected.retry_after > 0


def test_refill_over_time():
    clk = Clock()
    rl = RateLimiter(rps=2, burst=2, store=InMemoryBucketStore(2, 2, clk))
    assert rl.check("c").allowed and rl.check("c").allowed
    assert rl.check("c").allowed is False
    clk.advance(1)  # +2 tokens at 2 rps
    assert rl.check("c").allowed is True


def test_per_client_isolation():
    clk = Clock()
    rl = RateLimiter(rps=1, burst=1, store=InMemoryBucketStore(1, 1, clk))
    assert rl.check("a").allowed is True
    assert rl.check("b").allowed is True  # different client, own bucket
    assert rl.check("a").allowed is False


def test_middleware_returns_429_with_retry_after():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=RateLimiter(rps=5, burst=2))

    @app.get("/work")
    async def work():
        return {"ok": True}

    with TestClient(app) as c:
        codes = [c.get("/work").status_code for _ in range(4)]
        assert codes[:2] == [200, 200]
        assert 429 in codes
        r = c.get("/work")
        assert r.status_code == 429
        assert "retry-after" in {k.lower() for k in r.headers}
