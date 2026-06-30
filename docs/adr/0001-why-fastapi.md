# ADR-001: Why FastAPI for application services

**Status:** Accepted · **Date:** 2026-06

## Context
The api, auth, and worker services need an HTTP framework that supports: async
I/O (for non-blocking latency injection and cross-service calls), first-class
request/response validation, easy middleware (for global RED instrumentation),
and a small surface so the demo stays readable. The platform's whole point is
observability, so native ASGI middleware and `prometheus_client` interop matter.

## Decision
Use **FastAPI** (on Starlette/ASGI, with Pydantic models) for all Python
services, served by **uvicorn**.

## Consequences
- `BaseHTTPMiddleware` gives us one global RED + chaos middleware shared across
  services — no per-route instrumentation.
- Pydantic models enforce bounded chaos parameters (e.g. `delay_seconds` ≤ 10)
  with automatic `422` responses — safety for free.
- `async def` lets latency injection use `asyncio.sleep` without blocking the
  event loop, and lets the api call auth concurrently.
- Auto-generated OpenAPI docs (`/docs`) aid exploration.
- Trade-off: ASGI middleware ordering (last-added is outermost) is subtle; we
  document it where the rate limiter sits inside the Prometheus middleware.

## Alternatives considered
- **Flask** — mature, but synchronous by default; blocking sleeps would stall a
  worker and async dependency calls are awkward. No built-in validation.
- **Django** — far too heavy for a microservice demo; batteries we don't need.
- **Raw Starlette** — what FastAPI builds on; we'd lose Pydantic validation and
  OpenAPI for little gain.
