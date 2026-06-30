"""Shared observability: RED metrics, middleware, and system endpoints."""

from . import metrics
from .middleware import (
    PrometheusMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    route_label,
)
from .endpoints import build_system_router

__all__ = [
    "metrics",
    "PrometheusMiddleware",
    "RequestContextMiddleware",
    "SecurityHeadersMiddleware",
    "route_label",
    "build_system_router",
]
