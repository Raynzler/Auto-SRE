"""Health endpoint tests: /health and /ready for every service."""

from fastapi.testclient import TestClient
import pytest


@pytest.mark.parametrize("modname", ["api_module", "auth_module", "worker_module"])
def test_health_ok(request, modname):
    mod = request.getfixturevalue(modname)
    with TestClient(mod.app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "Healthy"
        assert body["service"] in ("api", "auth", "worker")
        assert "chaos" in body


@pytest.mark.parametrize("modname", ["api_module", "auth_module", "worker_module"])
def test_ready_ok(request, modname):
    mod = request.getfixturevalue(modname)
    with TestClient(mod.app) as c:
        r = c.get("/ready")
        assert r.status_code == 200
        assert r.json()["ready"] is True


def test_ready_degraded_503_when_error_chaos_active(api_module):
    with TestClient(api_module.app) as c:
        c.post("/chaos/errors", json={"enable": True, "rate_percent": 100})
        r = c.get("/ready")
        assert r.status_code == 503
        assert r.json()["ready"] is False
        c.post("/chaos/reset")
