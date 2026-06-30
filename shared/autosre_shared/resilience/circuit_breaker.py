"""Reusable circuit breaker framework (shared).

Tracks failures, rejects requests while open, exposes metrics. No remediation.
State lives behind BreakerStore (InMemory today, Redis-ready). Transitions are
persisted as failure events via the shared storage layer.
"""

import contextlib
import inspect
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge

from ..storage import record_event, Source


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


_STATE_VALUE = {BreakerState.CLOSED: 0, BreakerState.OPEN: 1, BreakerState.HALF_OPEN: 2}


@dataclass
class BreakerRecord:
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    opened_at: Optional[float] = None


class BreakerStore(ABC):
    @abstractmethod
    def load(self) -> BreakerRecord: ...

    @abstractmethod
    def save(self, record: BreakerRecord) -> None: ...


class InMemoryStore(BreakerStore):
    def __init__(self) -> None:
        self._record = BreakerRecord()

    def load(self) -> BreakerRecord:
        return self._record

    def save(self, record: BreakerRecord) -> None:
        self._record = record


circuit_breaker_state = Gauge(
    "circuit_breaker_state", "Circuit breaker state (0=closed, 1=open, 2=half_open)", ["name"]
)
circuit_breaker_open_total = Counter(
    "circuit_breaker_open_total", "Total number of times a breaker transitioned to OPEN", ["name"]
)
circuit_breaker_rejections_total = Counter(
    "circuit_breaker_rejections_total",
    "Total requests rejected because a breaker was OPEN",
    ["name"],
)


class CircuitBreakerOpenError(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"circuit breaker '{name}' is open")


class CircuitBreaker:
    def __init__(
        self,
        name,
        failure_threshold=5,
        recovery_timeout=30.0,
        success_threshold=2,
        store=None,
        expected_exceptions=(Exception,),
        clock=time.monotonic,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exceptions = expected_exceptions
        self._store = store or InMemoryStore()
        self._clock = clock
        self._lock = threading.Lock()
        rec = self._store.load()
        circuit_breaker_state.labels(name=self.name).set(_STATE_VALUE[rec.state])
        circuit_breaker_open_total.labels(name=self.name)
        circuit_breaker_rejections_total.labels(name=self.name)

    @property
    def state(self) -> BreakerState:
        return self._store.load().state

    def _set_state(self, rec, new_state):
        rec.state = new_state
        circuit_breaker_state.labels(name=self.name).set(_STATE_VALUE[new_state])

    def allow(self) -> bool:
        transitioned_half_open = False
        with self._lock:
            rec = self._store.load()
            if rec.state == BreakerState.OPEN:
                if self._clock() - (rec.opened_at or 0.0) < self.recovery_timeout:
                    return False
                rec.success_count = 0
                self._set_state(rec, BreakerState.HALF_OPEN)
                self._store.save(rec)
                transitioned_half_open = True
        if transitioned_half_open:
            record_event(Source.CIRCUIT_BREAKER, "half_open", name=self.name)
        return True

    def _reject(self):
        circuit_breaker_rejections_total.labels(name=self.name).inc()
        raise CircuitBreakerOpenError(self.name)

    def record_success(self):
        closed = False
        with self._lock:
            rec = self._store.load()
            if rec.state == BreakerState.HALF_OPEN:
                rec.success_count += 1
                if rec.success_count >= self.success_threshold:
                    rec.failure_count = 0
                    rec.success_count = 0
                    rec.opened_at = None
                    self._set_state(rec, BreakerState.CLOSED)
                    closed = True
            else:
                rec.failure_count = 0
            self._store.save(rec)
        if closed:
            record_event(Source.CIRCUIT_BREAKER, "closed", name=self.name)

    def record_failure(self):
        opened = False
        failure_count = 0
        with self._lock:
            rec = self._store.load()
            if rec.state == BreakerState.HALF_OPEN:
                rec.opened_at = self._clock()
                rec.success_count = 0
                self._set_state(rec, BreakerState.OPEN)
                circuit_breaker_open_total.labels(name=self.name).inc()
                opened = True
            else:
                rec.failure_count += 1
                if rec.failure_count >= self.failure_threshold:
                    rec.opened_at = self._clock()
                    self._set_state(rec, BreakerState.OPEN)
                    circuit_breaker_open_total.labels(name=self.name).inc()
                    opened = True
            failure_count = rec.failure_count
            self._store.save(rec)
        if opened:
            record_event(
                Source.CIRCUIT_BREAKER, "opened", name=self.name, failure_count=failure_count
            )

    def _enter(self):
        if not self.allow():
            self._reject()

    def _exit(self, failed):
        self.record_failure() if failed else self.record_success()

    @contextlib.asynccontextmanager
    async def protect(self):
        self._enter()
        try:
            yield self
        except self.expected_exceptions:
            self._exit(failed=True)
            raise
        else:
            self._exit(failed=False)

    @contextlib.contextmanager
    def guard(self):
        self._enter()
        try:
            yield self
        except self.expected_exceptions:
            self._exit(failed=True)
            raise
        else:
            self._exit(failed=False)

    async def call(self, func: Callable, *args, **kwargs):
        async with self.protect():
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result

    def snapshot(self) -> dict:
        rec = self._store.load()
        seconds_until_half_open = None
        if rec.state == BreakerState.OPEN and rec.opened_at is not None:
            remaining = self.recovery_timeout - (self._clock() - rec.opened_at)
            seconds_until_half_open = round(max(0.0, remaining), 2)
        return {
            "name": self.name,
            "state": rec.state.value,
            "failure_count": rec.failure_count,
            "success_count": rec.success_count,
            "seconds_until_half_open": seconds_until_half_open,
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "success_threshold": self.success_threshold,
            },
        }


_registry: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_or_create(name: str, **kwargs) -> CircuitBreaker:
    with _registry_lock:
        breaker = _registry.get(name)
        if breaker is None:
            breaker = CircuitBreaker(name, **kwargs)
            _registry[name] = breaker
        return breaker


def all_breakers() -> list[CircuitBreaker]:
    with _registry_lock:
        return list(_registry.values())


def reset_registry() -> None:
    with _registry_lock:
        _registry.clear()


def breaker_dependency(name: str, **kwargs) -> Callable[[], CircuitBreaker]:
    def _dependency() -> CircuitBreaker:
        return get_or_create(name, **kwargs)

    return _dependency


async def circuit_breaker_open_handler(request: Request, exc: Exception) -> JSONResponse:
    # Starlette types handlers as (Request, Exception); this is only registered
    # for CircuitBreakerOpenError, which carries `.name`.
    name = getattr(exc, "name", "unknown")
    return JSONResponse(
        status_code=503, content={"detail": str(exc), "circuit": name, "state": "open"}
    )


router = APIRouter(prefix="/breaker", tags=["resilience"])


@router.get("/status")
async def breaker_status():
    return {"breakers": [b.snapshot() for b in all_breakers()]}
