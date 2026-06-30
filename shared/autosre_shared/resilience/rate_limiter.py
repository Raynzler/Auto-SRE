"""Token bucket rate limiter (shared, middleware-based, Redis-ready)."""

import math
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..storage import record_event, Source

rate_limit_requests_total = Counter(
    "rate_limit_requests_total", "Total requests evaluated by the rate limiter"
)
rate_limit_rejections_total = Counter(
    "rate_limit_rejections_total", "Total requests rejected (HTTP 429) by the rate limiter"
)

_EXCLUDE_EXACT = frozenset(
    {"/", "/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json"}
)
_EXCLUDE_PREFIXES = ("/chaos", "/breaker", "/rate-limit", "/failures")


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: float
    retry_after: float


class BucketStore(ABC):
    @abstractmethod
    def consume(self, key: str, tokens: float = 1.0) -> RateLimitResult: ...

    @abstractmethod
    def active_keys(self) -> int: ...

    @abstractmethod
    def sample(self, limit: int = 20) -> dict: ...


class InMemoryBucketStore(BucketStore):
    def __init__(self, rps: float, burst: float, clock: Callable[[], float] = time.monotonic):
        self._rps = rps
        self._burst = burst
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def consume(self, key: str, tokens: float = 1.0) -> RateLimitResult:
        with self._lock:
            now = self._clock()
            cur, last = self._buckets.get(key, (self._burst, now))
            cur = min(self._burst, cur + (now - last) * self._rps)
            if cur >= tokens:
                cur -= tokens
                self._buckets[key] = (cur, now)
                return RateLimitResult(True, cur, 0.0)
            retry_after = (tokens - cur) / self._rps if self._rps > 0 else float("inf")
            self._buckets[key] = (cur, now)
            return RateLimitResult(False, cur, retry_after)

    def active_keys(self) -> int:
        with self._lock:
            return len(self._buckets)

    def sample(self, limit: int = 20) -> dict:
        with self._lock:
            return {k: round(v[0], 2) for k, v in list(self._buckets.items())[:limit]}


class RateLimiter:
    def __init__(self, rps, burst, store=None, clock=time.monotonic):
        self.rps = rps
        self.burst = burst
        self._store = store or InMemoryBucketStore(rps, burst, clock)

    def check(self, key: str) -> RateLimitResult:
        rate_limit_requests_total.inc()
        result = self._store.consume(key)
        if not result.allowed:
            rate_limit_rejections_total.inc()
        return result

    def snapshot(self) -> dict:
        return {
            "config": {"requests_per_second": self.rps, "burst_capacity": self.burst},
            "active_clients": self._store.active_keys(),
            "sample": self._store.sample(),
        }


_default: Optional[RateLimiter] = None
_default_lock = threading.Lock()


def get_limiter() -> RateLimiter:
    global _default
    if _default is None:
        with _default_lock:
            if _default is None:
                rps = float(os.getenv("RATE_LIMIT_RPS", "10"))
                burst = float(os.getenv("RATE_LIMIT_BURST", "20"))
                _default = RateLimiter(rps, burst)
    return _default


def set_limiter(limiter: RateLimiter) -> None:
    global _default
    _default = limiter


def _client_key(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _excluded(path: str) -> bool:
    return path in _EXCLUDE_EXACT or any(path.startswith(p) for p in _EXCLUDE_PREFIXES)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self._limiter = limiter or get_limiter()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _excluded(path):
            return await call_next(request)

        key = _client_key(request)
        result = self._limiter.check(key)
        if not result.allowed:
            retry = max(1, math.ceil(result.retry_after))
            record_event(Source.RATE_LIMIT, "rejected", client=key, path=path, retry_after=retry)
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "retry_after": retry},
                headers={"Retry-After": str(retry)},
            )
        return await call_next(request)


router = APIRouter(prefix="/rate-limit", tags=["resilience"])


@router.get("/status")
async def rate_limit_status():
    return get_limiter().snapshot()
