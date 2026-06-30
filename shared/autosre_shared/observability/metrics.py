"""Shared RED + saturation metric definitions.

Each service runs in its own process, so these module-level singletons are
per-service; Prometheus separates them by the `job` label set in the scrape
config. Buckets are SLO-aligned (200/300ms, 500/750ms).
"""

from prometheus_client import Counter, Gauge, Histogram

LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.2,
    0.3,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=LATENCY_BUCKETS,
)
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)
http_exceptions_total = Counter(
    "http_exceptions_total",
    "Total unhandled exceptions raised while handling requests",
    ["method", "endpoint", "exception_type"],
)
service_up = Gauge(
    "service_up",
    "Service health status (1=up, 0=down)",
    [],
)
