"""Chaos engineering framework (shared, per-service controller).

Each service instantiates one ChaosController. It injects bounded, reversible
failure (latency, errors, CPU, memory) so the observability stack has something
to detect. It performs NO remediation. Metric names are shared across services;
Prometheus separates them by the `job` label.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from prometheus_client import Counter, Gauge, Histogram
from starlette.requests import Request
from starlette.responses import Response

from .storage import record_event, Source

logger = logging.getLogger("autosre.chaos")

# Safety bounds (also enforced via Pydantic).
LATENCY_MAX_SECONDS = 10.0
CPU_MAX_SECONDS = 30.0
MEMORY_MAX_MB = 256.0
MEMORY_HOLD_MAX_SECONDS = 60.0
_MEMORY_MAX_BYTES = int(MEMORY_MAX_MB * 1024 * 1024)

_CONTROL_PATHS = frozenset({"/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json"})
_CONTROL_PREFIXES = ("/chaos", "/breaker", "/rate-limit", "/failures")

# Shared metric definitions (one per process).
chaos_events_total = Counter(
    "chaos_events_total", "Total chaos control-plane events", ["type", "action"]
)
chaos_active = Gauge(
    "chaos_active", "Whether a chaos mode is active (1=active, 0=inactive)", ["type"]
)
chaos_latency_seconds = Histogram(
    "chaos_latency_seconds",
    "Latency injected into requests, in seconds",
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0, 10.0),
)
chaos_error_injections_total = Counter(
    "chaos_error_injections_total", "Total HTTP 500 responses injected by chaos"
)


@dataclass
class ChaosState:
    latency_enabled: bool = False
    latency_seconds: float = 0.0
    error_enabled: bool = False
    error_rate: float = 0.0
    _error_accumulator: float = 0.0
    cpu_running: bool = False
    memory_bytes: int = 0
    _memory_blocks: list = field(default_factory=list)
    _tasks: set = field(default_factory=set)

    def is_active(self) -> bool:
        return (
            self.latency_enabled or self.error_enabled or self.cpu_running or self.memory_bytes > 0
        )

    def should_inject_error(self) -> bool:
        """Deterministic, evenly-spread error decision (Bresenham accumulator)."""
        if not (self.error_enabled and self.error_rate > 0):
            return False
        self._error_accumulator += self.error_rate
        if self._error_accumulator >= 1.0:
            self._error_accumulator -= 1.0
            return True
        return False

    def snapshot(self) -> dict:
        return {
            "active": self.is_active(),
            "latency": {"enabled": self.latency_enabled, "seconds": round(self.latency_seconds, 3)},
            "errors": {
                "enabled": self.error_enabled,
                "rate_percent": round(self.error_rate * 100, 2),
            },
            "cpu": {"running": self.cpu_running},
            "memory": {
                "allocated_mb": round(self.memory_bytes / 1024 / 1024, 2),
                "blocks": len(self._memory_blocks),
            },
        }

    def track(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


class _StrictModel(BaseModel):
    # Reject unknown fields on all chaos control payloads.
    model_config = ConfigDict(extra="forbid")


class LatencyConfig(_StrictModel):
    enable: bool
    delay_seconds: float = Field(1.0, ge=0.0, le=LATENCY_MAX_SECONDS)


class ErrorConfig(_StrictModel):
    enable: bool
    rate_percent: float = Field(50.0, ge=0.0, le=100.0)


class CPUConfig(_StrictModel):
    duration_seconds: float = Field(5.0, gt=0.0, le=CPU_MAX_SECONDS)


class MemoryConfig(_StrictModel):
    size_mb: float = Field(64.0, gt=0.0, le=MEMORY_MAX_MB)
    hold_seconds: float = Field(10.0, gt=0.0, le=MEMORY_HOLD_MAX_SECONDS)


def _cpu_burn(deadline: float) -> None:
    x = 0
    while time.perf_counter() < deadline:
        x += 1  # noqa: F841 - intentional busy work


class ChaosController:
    def __init__(self, service_name: str = "service"):
        self.service = service_name
        self.state = ChaosState()
        for t in ("latency", "errors", "cpu", "memory"):
            chaos_active.labels(type=t).set(0)
        self.router = self._build_router()

    # --- data plane ---
    async def apply_request_chaos(self, request: Request) -> Optional[Response]:
        path = request.url.path
        if path in _CONTROL_PATHS or any(path.startswith(p) for p in _CONTROL_PREFIXES):
            return None

        s = self.state
        if s.latency_enabled and s.latency_seconds > 0:
            await asyncio.sleep(s.latency_seconds)
            chaos_latency_seconds.observe(s.latency_seconds)

        if s.should_inject_error():
            chaos_error_injections_total.inc()
            logger.debug("injected HTTP 500 on %s", path)
            return JSONResponse(
                status_code=500, content={"detail": "chaos: injected error", "injected": True}
            )
        return None

    # --- background workloads ---
    async def _run_cpu(self, duration: float) -> None:
        chaos_active.labels(type="cpu").set(1)
        self.state.cpu_running = True
        deadline = time.perf_counter() + duration
        try:
            await asyncio.to_thread(_cpu_burn, deadline)
        finally:
            self.state.cpu_running = False
            chaos_active.labels(type="cpu").set(0)
            logger.warning("CPU chaos finished after %.1fs", duration)

    async def _run_memory(self, size_bytes: int, hold: float) -> None:
        block = bytearray(size_bytes)
        for i in range(0, size_bytes, 4096):
            block[i] = 1
        self.state._memory_blocks.append(block)
        self.state.memory_bytes += size_bytes
        chaos_active.labels(type="memory").set(1)
        logger.warning("memory chaos: allocated %.1f MB for %.1fs", size_bytes / 1024 / 1024, hold)
        try:
            await asyncio.sleep(hold)
        finally:
            try:
                self.state._memory_blocks.remove(block)
            except ValueError:
                pass
            self.state.memory_bytes = max(0, self.state.memory_bytes - size_bytes)
            del block
            if self.state.memory_bytes <= 0:
                chaos_active.labels(type="memory").set(0)

    # --- control plane router ---
    def _build_router(self) -> APIRouter:
        router = APIRouter(prefix="/chaos", tags=["chaos"])
        s = self.state

        @router.post("/latency")
        async def set_latency(cfg: LatencyConfig):
            s.latency_enabled = cfg.enable
            s.latency_seconds = cfg.delay_seconds if cfg.enable else 0.0
            chaos_active.labels(type="latency").set(1 if cfg.enable else 0)
            action = "enable" if cfg.enable else "disable"
            chaos_events_total.labels(type="latency", action=action).inc()
            record_event(
                Source.CHAOS, f"latency_{action}", service=self.service, seconds=s.latency_seconds
            )
            logger.warning("chaos latency %sd at %.3fs", action, s.latency_seconds)
            return {"status": "ok", "chaos": s.snapshot()}

        @router.post("/errors")
        async def set_errors(cfg: ErrorConfig):
            s.error_enabled = cfg.enable
            s.error_rate = (cfg.rate_percent / 100.0) if cfg.enable else 0.0
            s._error_accumulator = 0.0
            chaos_active.labels(type="errors").set(1 if cfg.enable else 0)
            action = "enable" if cfg.enable else "disable"
            chaos_events_total.labels(type="errors", action=action).inc()
            record_event(
                Source.CHAOS,
                f"errors_{action}",
                service=self.service,
                rate_percent=cfg.rate_percent if cfg.enable else 0.0,
            )
            logger.warning(
                "chaos errors %sd at %.1f%%", action, cfg.rate_percent if cfg.enable else 0
            )
            return {"status": "ok", "chaos": s.snapshot()}

        @router.post("/cpu")
        async def trigger_cpu(cfg: CPUConfig):
            chaos_events_total.labels(type="cpu", action="trigger").inc()
            record_event(
                Source.CHAOS,
                "cpu_trigger",
                service=self.service,
                duration_seconds=cfg.duration_seconds,
            )
            s.track(self._run_cpu(cfg.duration_seconds))
            logger.warning("chaos CPU triggered for %.1fs", cfg.duration_seconds)
            return {
                "status": "started",
                "cpu": {"duration_seconds": cfg.duration_seconds},
                "chaos": s.snapshot(),
            }

        @router.post("/memory")
        async def trigger_memory(cfg: MemoryConfig):
            size_bytes = int(cfg.size_mb * 1024 * 1024)
            if s.memory_bytes + size_bytes > _MEMORY_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"requested {cfg.size_mb} MB would exceed the {MEMORY_MAX_MB} MB cap "
                        f"(currently held: {s.memory_bytes / 1024 / 1024:.1f} MB)"
                    ),
                )
            chaos_events_total.labels(type="memory", action="trigger").inc()
            record_event(
                Source.CHAOS,
                "memory_trigger",
                service=self.service,
                size_mb=cfg.size_mb,
                hold_seconds=cfg.hold_seconds,
            )
            s.track(self._run_memory(size_bytes, cfg.hold_seconds))
            logger.warning(
                "chaos memory triggered: %.1f MB for %.1fs", cfg.size_mb, cfg.hold_seconds
            )
            return {
                "status": "started",
                "memory": {"size_mb": cfg.size_mb, "hold_seconds": cfg.hold_seconds},
                "chaos": s.snapshot(),
            }

        @router.post("/reset")
        async def reset():
            s.latency_enabled = False
            s.latency_seconds = 0.0
            s.error_enabled = False
            s.error_rate = 0.0
            s._error_accumulator = 0.0
            s._memory_blocks.clear()
            s.memory_bytes = 0
            chaos_active.labels(type="latency").set(0)
            chaos_active.labels(type="errors").set(0)
            chaos_active.labels(type="memory").set(0)
            chaos_events_total.labels(type="reset", action="reset").inc()
            record_event(Source.CHAOS, "reset", service=self.service)
            logger.warning("chaos reset to default state")
            return {"status": "reset", "chaos": s.snapshot()}

        @router.get("/status")
        async def status():
            return s.snapshot()

        return router
