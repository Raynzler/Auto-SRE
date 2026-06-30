"""Shared system endpoints: /health, /ready, /metrics."""

import inspect

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


def build_system_router(service_name: str, chaos, readiness_check=None) -> APIRouter:
    """Build the /health, /ready, /metrics router for a service.

    readiness_check: optional callable (sync or async) returning a bool or a
    dict like {"ready": bool, ...} for service-specific dependency checks.
    """
    router = APIRouter(tags=["system"])

    @router.get("/health")
    async def health():
        # Liveness: always 200 if the process is alive; surfaces chaos state.
        return {"status": "Healthy", "service": service_name, "chaos": chaos.state.snapshot()}

    @router.get("/ready")
    async def ready():
        snapshot = chaos.state.snapshot()
        ok = not chaos.state.error_enabled
        checks = {}
        if ok and readiness_check is not None:
            result = readiness_check()
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, dict):
                checks = result
                ok = bool(result.get("ready", True))
            else:
                ok = bool(result)
        payload = {
            "status": "ready" if ok else "degraded",
            "ready": ok,
            "service": service_name,
            "chaos": snapshot,
        }
        if checks:
            payload["checks"] = checks
        return JSONResponse(status_code=200 if ok else 503, content=payload)

    @router.get("/metrics")
    async def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return router
