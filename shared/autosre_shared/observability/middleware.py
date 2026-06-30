"""Global RED instrumentation + request-context + security-header middleware."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..context import correlation_id_var, new_id, request_id_var
from .metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_exceptions_total,
)


def _scope_header(scope, name: bytes):
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


class RequestContextMiddleware:
    """Pure-ASGI middleware that assigns request and correlation IDs.

    Reads X-Request-ID / X-Correlation-ID if present (else generates them),
    binds them to contextvars for logging + downstream propagation, and echoes
    them back on the response. Implemented as pure ASGI (not BaseHTTPMiddleware)
    so the contextvars reliably propagate to the handler and logger.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = _scope_header(scope, b"x-request-id") or new_id()
        cid = _scope_header(scope, b"x-correlation-id") or rid
        rtok = request_id_var.set(rid)
        ctok = correlation_id_var.set(cid)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", rid.encode("latin-1")))
                headers.append((b"x-correlation-id", cid.encode("latin-1")))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(rtok)
            correlation_id_var.reset(ctok)


_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
]
_CSP = b"default-src 'none'; frame-ancestors 'none'"
# Interactive docs load assets from a CDN; a strict CSP would break them.
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    """Pure-ASGI middleware adding standard security response headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(_SECURITY_HEADERS)
                if not path.startswith(_DOCS_PATHS):
                    headers.append((b"content-security-policy", _CSP))
            await send(message)

        await self.app(scope, receive, send_wrapper)


def route_label(request: Request) -> str:
    """Matched route template (bounded cardinality), falling back to raw path."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Records RED metrics for every request and applies per-service chaos.

    `chaos` is an optional object exposing `apply_request_chaos(request)` that
    returns a Response to short-circuit (injected error) or None.
    """

    def __init__(self, app, chaos=None):
        super().__init__(app)
        self._chaos = chaos

    async def dispatch(self, request: Request, call_next):
        method = request.method
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.perf_counter()
        http_requests_in_progress.labels(method=method).inc()

        status_code = "500"
        try:
            if self._chaos is not None:
                injected = await self._chaos.apply_request_chaos(request)
                if injected is not None:
                    status_code = str(injected.status_code)
                    return injected

            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception as exc:
            http_exceptions_total.labels(
                method=method,
                endpoint=route_label(request),
                exception_type=type(exc).__name__,
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start_time
            endpoint = route_label(request)
            http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
            http_requests_in_progress.labels(method=method).dec()
