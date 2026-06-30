"""Hardening tests: security headers, request/correlation IDs, env + input validation."""

import pytest
from fastapi.testclient import TestClient

from autosre_shared.context import correlation_id_var, propagation_headers
from autosre_shared.envcheck import validate_env


def test_security_headers_present(api_module):
    with TestClient(api_module.app) as c:
        r = c.get("/health")
        h = {k.lower(): v for k, v in r.headers.items()}
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert "referrer-policy" in h
        assert "content-security-policy" in h


def test_request_id_generated_and_echoed(api_module):
    with TestClient(api_module.app) as c:
        r = c.get("/health")
        assert r.headers.get("x-request-id")
        assert r.headers.get("x-correlation-id")


def test_inbound_request_id_is_honored(api_module):
    with TestClient(api_module.app) as c:
        r = c.get("/health", headers={"X-Request-ID": "abc123", "X-Correlation-ID": "corr-9"})
        assert r.headers["x-request-id"] == "abc123"
        assert r.headers["x-correlation-id"] == "corr-9"


def test_propagation_headers_carry_correlation():
    token = correlation_id_var.set("corr-xyz")
    try:
        assert propagation_headers() == {"X-Correlation-ID": "corr-xyz"}
    finally:
        correlation_id_var.reset(token)


def test_propagation_headers_empty_without_context():
    # Default contextvar value ("-") yields no propagation header.
    assert propagation_headers() == {}


def test_input_validation_rejects_unknown_fields(api_module, fake_auth_ok, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_ok)
    with TestClient(api_module.app) as c:
        r = c.post("/orders", json={"item": "x", "quantity": 1, "evil": True})
        assert r.status_code == 422  # extra="forbid"


def test_input_validation_rejects_out_of_range(api_module, fake_auth_ok, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_ok)
    with TestClient(api_module.app) as c:
        assert c.post("/orders", json={"item": "x", "quantity": 0}).status_code == 422
        assert c.post("/orders", json={"item": "", "quantity": 1}).status_code == 422


def test_validate_env_passes_with_valid_values(monkeypatch):
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.setenv("RATE_LIMIT_RPS", "10")
    validate_env()  # should not raise


def test_validate_env_fails_on_bad_numeric(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-number")
    with pytest.raises(RuntimeError, match="environment validation failed"):
        validate_env()


def test_validate_env_fails_on_missing_required(monkeypatch):
    monkeypatch.delenv("DEFINITELY_MISSING", raising=False)
    with pytest.raises(RuntimeError, match="missing required env var"):
        validate_env(required=("DEFINITELY_MISSING",))
