"""Chaos validation tests: injection works, is bounded, and never locks out."""

import time

from fastapi.testclient import TestClient


def test_latency_injection_delays_requests(api_module):
    with TestClient(api_module.app) as c:
        assert (
            c.post("/chaos/latency", json={"enable": True, "delay_seconds": 0.3}).status_code == 200
        )
        start = time.perf_counter()
        c.get("/probe")  # non-control path: 404, but injected latency still applies
        assert time.perf_counter() - start >= 0.3
        c.post("/chaos/reset")


def test_error_injection_is_deterministic(api_module):
    with TestClient(api_module.app) as c:
        c.post("/chaos/errors", json={"enable": True, "rate_percent": 50})
        codes = [c.get("/probe").status_code for _ in range(10)]
        assert codes.count(500) == 5  # injected 500s; others fall through to 404
        c.post("/chaos/reset")


def test_control_paths_never_injected(api_module):
    with TestClient(api_module.app) as c:
        c.post("/chaos/errors", json={"enable": True, "rate_percent": 100})
        # Even at 100% error injection, control/observability paths must work
        assert c.get("/health").status_code == 200
        assert c.get("/chaos/status").status_code == 200
        assert c.get("/metrics").status_code == 200
        assert c.post("/chaos/reset").status_code == 200


def test_bounds_enforced_422(api_module):
    with TestClient(api_module.app) as c:
        assert (
            c.post("/chaos/latency", json={"enable": True, "delay_seconds": 99}).status_code == 422
        )
        assert c.post("/chaos/memory", json={"size_mb": 99999}).status_code == 422
        assert (
            c.post("/chaos/latency", json={"delay_seconds": 1}).status_code == 422
        )  # enable required


def test_reset_clears_state(api_module):
    with TestClient(api_module.app) as c:
        c.post("/chaos/latency", json={"enable": True, "delay_seconds": 1})
        assert c.post("/chaos/reset").json()["chaos"]["active"] is False
        assert c.get("/chaos/status").json()["active"] is False


def test_cpu_and_memory_are_bounded_oneshots(api_module):
    with TestClient(api_module.app) as c:
        assert c.post("/chaos/cpu", json={"duration_seconds": 0.1}).json()["status"] == "started"
        assert (
            c.post("/chaos/memory", json={"size_mb": 4, "hold_seconds": 0.1}).json()["status"]
            == "started"
        )
        time.sleep(0.3)  # let the bounded workloads finish
