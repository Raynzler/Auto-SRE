"""Metrics + Prometheus endpoint tests."""

from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families


def test_metrics_endpoint_is_valid_prometheus_format(api_module):
    with TestClient(api_module.app) as c:
        r = c.get("/metrics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        # If this parses without raising, the exposition format is valid.
        families = list(text_string_to_metric_families(r.text))
        assert len(families) > 0


def test_red_and_subsystem_metrics_present(api_module):
    with TestClient(api_module.app) as c:
        # Generate some traffic and touch each subsystem router.
        c.get("/probe")
        c.get("/probe")
        c.post("/chaos/reset")
        c.get("/breaker/status")
        c.get("/rate-limit/status")
        text = c.get("/metrics").text

    expected = [
        "http_requests_total",  # Rate + Errors
        "http_request_duration_seconds_bucket",  # Duration (histogram)
        "http_requests_in_progress",  # Saturation
        "service_up",
        "chaos_active",
        "chaos_events_total",
        "circuit_breaker_state",
        "rate_limit_requests_total",
    ]
    for name in expected:
        assert name in text, f"missing metric: {name}"


def test_injected_errors_appear_in_red_metrics(api_module):
    with TestClient(api_module.app) as c:
        c.post("/chaos/errors", json={"enable": True, "rate_percent": 100})
        c.get("/probe")  # forced 500 via chaos
        c.post("/chaos/reset")
        text = c.get("/metrics").text
        assert 'status="500"' in text
        assert "chaos_error_injections_total" in text
