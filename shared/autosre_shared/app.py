"""Application factory shared by every AutoSRE service.

create_service_app wires the common platform — structured logging, RED
middleware, per-service chaos, optional rate limiting, the circuit breaker /
rate-limit / chaos / failures routers, system endpoints, and lifespan — so each
service file only declares its own business routers and behaviour.
"""

import inspect
from contextlib import asynccontextmanager
from typing import Callable, Iterable, Optional

from fastapi import FastAPI

from .envcheck import validate_env
from .logging import configure_logging
from .observability.metrics import service_up
from .observability.middleware import (
    PrometheusMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from .observability.endpoints import build_system_router
from .chaos import ChaosController
from .resilience.circuit_breaker import (
    router as breaker_router,
    CircuitBreakerOpenError,
    circuit_breaker_open_handler,
)
from .resilience.rate_limiter import RateLimitMiddleware, router as rate_limit_router
from .storage import failures_router


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


def create_service_app(
    *,
    service_name: str,
    title: Optional[str] = None,
    version: str = "1.0.0",
    enable_rate_limit: bool = True,
    business_routers: Optional[Iterable] = None,
    readiness_check: Optional[Callable] = None,
    on_startup: Optional[Callable[[FastAPI], object]] = None,
    on_shutdown: Optional[Callable[[FastAPI], object]] = None,
    required_env: tuple[str, ...] = (),
) -> FastAPI:
    # Fail fast on a malformed/missing environment before building the app.
    validate_env(required_env)

    logger = configure_logging(service_name)
    chaos = ChaosController(service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service_up.set(1)
        logger.info("service started", extra={"service": service_name})
        if on_startup is not None:
            await _maybe_await(on_startup(app))
        yield
        if on_shutdown is not None:
            await _maybe_await(on_shutdown(app))
        service_up.set(0)
        logger.info("service stopping", extra={"service": service_name})

    app = FastAPI(title=title or f"AutoSRE {service_name}", version=version, lifespan=lifespan)

    # Middleware order: last added is outermost. Innermost-to-outermost:
    # RateLimit -> Prometheus (measures injected 429s) -> SecurityHeaders ->
    # RequestContext (outermost, so request/correlation IDs are set before
    # anything else runs or logs).
    if enable_rate_limit:
        app.add_middleware(RateLimitMiddleware)
    app.add_middleware(PrometheusMiddleware, chaos=chaos)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.add_exception_handler(CircuitBreakerOpenError, circuit_breaker_open_handler)

    app.include_router(build_system_router(service_name, chaos, readiness_check))
    app.include_router(chaos.router)
    app.include_router(breaker_router)
    app.include_router(rate_limit_router)
    app.include_router(failures_router)
    for r in business_routers or []:
        app.include_router(r)

    app.state.chaos = chaos
    app.state.logger = logger
    return app
