"""Integration tests: cross-service api -> auth via the ServiceClient abstraction."""

from fastapi.testclient import TestClient

from autosre_shared.resilience import reset_registry


def test_api_calls_auth_through_abstraction(api_module, fake_auth_ok, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_ok)
    with TestClient(api_module.app) as c:
        assert c.post("/orders", json={"item": "x", "quantity": 1}).status_code == 200


def test_breaker_opens_on_auth_outage_and_is_visible(api_module, fake_auth_down, monkeypatch):
    reset_registry()
    monkeypatch.setattr(api_module, "auth_client", fake_auth_down)
    with TestClient(api_module.app) as c:
        for _ in range(5):
            c.post("/orders", json={"item": "x", "quantity": 1})
        assert c.post("/orders", json={"item": "x", "quantity": 1}).status_code == 503
        breakers = {b["name"]: b for b in c.get("/breaker/status").json()["breakers"]}
        assert breakers["auth"]["state"] == "open"


def test_auth_validates_tokens(auth_module):
    with TestClient(auth_module.app) as c:
        assert c.post("/validate", json={"token": "good"}).json()["valid"] is True
        assert c.post("/validate", json={"token": "invalid"}).json()["valid"] is False
