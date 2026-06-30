"""API tests: order creation behaviour and its failure modes."""

from fastapi.testclient import TestClient

from autosre_shared.resilience import reset_registry


def test_order_success_with_valid_auth(api_module, fake_auth_ok, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_ok)
    with TestClient(api_module.app) as c:
        r = c.post(
            "/orders", json={"item": "laptop", "quantity": 1}, headers={"Authorization": "Bearer t"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "created" and body["order_id"].startswith("order_")


def test_order_invalid_token_401(api_module, fake_auth_invalid, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_invalid)
    with TestClient(api_module.app) as c:
        assert c.post("/orders", json={"item": "x", "quantity": 1}).status_code == 401


def test_order_bad_body_422(api_module):
    with TestClient(api_module.app) as c:
        # missing required 'quantity' -> Pydantic validation error before handler
        assert c.post("/orders", json={"item": "x"}).status_code == 422


def test_order_dependency_down_502(api_module, fake_auth_down, monkeypatch):
    monkeypatch.setattr(api_module, "auth_client", fake_auth_down)
    with TestClient(api_module.app) as c:
        assert c.post("/orders", json={"item": "x", "quantity": 1}).status_code == 502


def test_order_breaker_open_503(api_module, fake_auth_down, monkeypatch):
    reset_registry()
    monkeypatch.setattr(api_module, "auth_client", fake_auth_down)
    with TestClient(api_module.app) as c:
        codes = [c.post("/orders", json={"item": "x", "quantity": 1}).status_code for _ in range(5)]
        assert codes == [502] * 5  # 5 failures trip the breaker
        assert c.post("/orders", json={"item": "x", "quantity": 1}).status_code == 503
